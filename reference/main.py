from flask import Flask, request, Response, render_template, redirect, session, url_for, jsonify
from dotenv import load_dotenv
import json
import os
import requests
from datetime import datetime, timedelta
from database import (
    init_db, save_message, get_messages, save_user_info, 
    get_user_info, save_auth_token, get_auth_token  # Added these
)
from instagram_api import InstagramAPI
from message_handler import MessageHandler
import secrets  # Add this import

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Check for secret key in environment or generate a new one
if not os.getenv('FLASK_SECRET_KEY'):
    print("⚠️ No FLASK_SECRET_KEY found in .env, generating a random one")
    print("⚠️ Note: Sessions will be invalidated on server restart")
    app.secret_key = secrets.token_hex(16)
else:
    app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Initialize database
init_db()

# Instagram OAuth Configuration
INSTAGRAM_CLIENT_ID = os.getenv('INSTAGRAM_CLIENT_ID')
INSTAGRAM_CLIENT_SECRET = os.getenv('INSTAGRAM_CLIENT_SECRET')
REDIRECT_URI = os.getenv('INSTAGRAM_REDIRECT_URI')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

def get_instagram_business_account(access_token):
    """Get Instagram Business Account ID using Instagram Graph API"""
    try:
        # Use Instagram Graph API directly
        response = requests.get('https://graph.instagram.com/v19.0/me', params={
            'access_token': access_token,
            'fields': 'id,username'
        })
        print("Instagram account response:", response.text)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('id')
            
        return None
    except Exception as e:
        print(f"Error getting Instagram account: {e}")
        return None

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/auth')
def auth():
    # Full list of available Instagram business scopes
    scopes = [
        'instagram_business_manage_messages'    # Manage messages
        #'instagram_business_manage_comments'     # Manage comments
    ]
    
    instagram_auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?client_id={INSTAGRAM_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={','.join(scopes)}"
        f"&response_type=code"
    )
    print(f"Auth URL: {instagram_auth_url}")  # Debug print
    return redirect(instagram_auth_url)

@app.route('/callback')
def callback():
    print(f"Received callback with args: {request.args}")  # Debug print
    code = request.args.get('code')
    if not code:
        return 'Error: No code received', 400

    try:
        # Get short-lived token
        short_lived_token_response = exchange_code_for_token(code)
        if not short_lived_token_response:
            return 'Error getting short-lived access token', 400

        print("Short-lived token response:", short_lived_token_response)  # Debug print
        
        # Convert to long-lived token
        long_lived_token = convert_to_long_lived_token(short_lived_token_response['access_token'])
        if not long_lived_token:
            return 'Error converting to long-lived token', 400

        # Store tokens in session
        session['access_token'] = long_lived_token['access_token']
        session['token_expires'] = datetime.now() + timedelta(days=60)
        
        # Get Instagram account ID from webhook or stored value
        ig_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')  # Add this to .env
        if not ig_account_id:
            ig_account_id = get_instagram_business_account(long_lived_token['access_token'])
        
        if ig_account_id:
            # Store the token with Instagram account ID
            save_auth_token(
                ig_business_id=ig_account_id,
                access_token=long_lived_token['access_token'],
                expires_at=datetime.now() + timedelta(days=60)
            )
            print(f"Stored token for Instagram account: {ig_account_id}")
            session['instagram_account_id'] = ig_account_id
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Token exchange error: {e}")
        return f'Authentication failed: {str(e)}', 400

def exchange_code_for_token(code):
    try:
        response = requests.post('https://api.instagram.com/oauth/access_token', data={
            'client_id': INSTAGRAM_CLIENT_ID,
            'client_secret': INSTAGRAM_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'code': code
        })
        print("Short-lived token response:", response.text)  # Debug print
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error in exchange_code_for_token: {e}")
        return None

def convert_to_long_lived_token(short_lived_token):
    try:
        response = requests.get('https://graph.instagram.com/access_token', params={
            'client_secret': INSTAGRAM_CLIENT_SECRET,
            'access_token': short_lived_token,
            'grant_type': 'ig_exchange_token'
        })
        print("Long-lived token response:", response.text)  # Debug print
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error in convert_to_long_lived_token: {e}")
        return None

def refresh_token(token):
    response = requests.get(os.getenv('TOKEN_REFRESH_URL'), params={
        'grant_type': 'ig_refresh_token',
        'access_token': token
    })
    return response.json() if response.status_code == 200 else None

def get_account_info(access_token):
    """Get Instagram account info using Instagram Graph API"""
    try:
        response = requests.get('https://graph.instagram.com/v19.0/me', params={
            'access_token': access_token,
            'fields': 'id,username,account_type,media_count'
        })
        print("Instagram account info response:", response.text)
        
        if response.status_code == 200:
            data = response.json()
            # Format the response to match the template expectations
            return {
                'instagram_business_account': {
                    'id': data.get('id'),
                    'username': data.get('username'),
                    'name': data.get('username'),  # Instagram API doesn't provide name
                    'profile_picture_url': None  # Instagram API doesn't provide profile pic
                }
            }
        return None
    except Exception as e:
        print(f"Error getting account info: {e}")
        return None

@app.route('/dashboard')
@app.route('/dashboard/')
def dashboard():
    if 'access_token' not in session:
        return redirect(url_for('login'))
    
    session['last_access'] = datetime.now().isoformat()
    
    # Debug prints
    print("=== Dashboard Route Debug ===")
    print("Session token:", session.get('access_token')[:10] + "...")
    print("Current URL:", request.url)
    
    # Direct redirect to Streamlit with proper path
    return redirect('https://b4fvhl4w-8501.brs.devtunnels.ms/dashboard/', code=302)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Handle the verification request from Instagram
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                print("WEBHOOK_VERIFIED")
                return challenge
            else:
                return Response('Forbidden', status=403)

    elif request.method == 'POST':
        try:
            data = json.loads(request.data.decode('utf-8'))
            print("Received webhook data:", data)
            
            if 'entry' in data and len(data['entry']) > 0:
                entry = data['entry'][0]
                recipient_id = entry.get('id')
                
                messaging = entry.get('messaging', [])
                if messaging:
                    message = messaging[0]
                    sender_id = message.get('sender', {}).get('id')
                    text = message.get('message', {}).get('text')
                    
                    # Only proceed if we have valid sender and message
                    if sender_id and text:
                        # Skip if sender is our Instagram account
                        our_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
                        if sender_id == our_account_id:
                            print(f"Skipping our own message from {sender_id}")
                            return 'EVENT_RECEIVED'
                        
                        # Get token to use
                        token_to_use = None
                        stored_token = get_auth_token(recipient_id)
                        
                        if stored_token and stored_token.get('access_token'):
                            token_to_use = stored_token['access_token']
                        elif 'access_token' in session:
                            token_to_use = session['access_token']
                        else:
                            token_to_use = os.getenv('INSTAGRAM_PAGE_ACCESS_TOKEN')

                        if not token_to_use:
                            print("No valid token found")
                            return 'No valid token found', 400
                            
                        # Handle message with new handler
                        handler = MessageHandler(token_to_use, recipient_id)
                        if handler.handle_incoming_message(sender_id, text):
                            return 'EVENT_RECEIVED'
                        else:
                            return 'Failed to process message', 400
                        
            return 'EVENT_RECEIVED'
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return Response('Bad Request', status=400)

@app.route('/deauthorize', methods=['POST'])
def deauthorize():
    try:
        data = json.loads(request.data.decode('utf-8'))
        user_id = data.get('signed_request', {}).get('user_id')
        
        if user_id:
            # TODO: Clean up user data from your database
            print(f"Deauthorized user: {user_id}")
            
        return Response('', status=200)
    except Exception as e:
        print(f"Deauthorization error: {e}")
        return Response('Bad Request', status=400)

@app.route('/delete-data', methods=['POST'])
def delete_data():
    try:
        data = json.loads(request.data.decode('utf-8'))
        user_id = data.get('signed_request', {}).get('user_id')
        
        if user_id:
            # TODO: Implement permanent data deletion for the user
            print(f"Data deletion request for user: {user_id}")
            
        return Response('', status=200)
    except Exception as e:
        print(f"Data deletion error: {e}")
        return Response('Bad Request', status=400)

if __name__ == '__main__':
    app.run(port=7777, debug=True)