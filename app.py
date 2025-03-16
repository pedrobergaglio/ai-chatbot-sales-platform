import requests
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, Response
import os
import json
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps
import logging
from flask import request, g
import time

# Import utility modules
from database import (
    init_db, get_db, save_message, get_user_messages, get_users_by_status, set_conversation_status,
    get_user_info, save_auth_token, get_auth_token, get_conversation_status, get_users_by_status_and_platform
)
from instagram_api import InstagramAPI
from whatsapp_api import WhatsAppAPI
from message_handler import InstagramMessageHandler, WhatsAppMessageHandler

# Add this near the imports
from werkzeug.security import check_password_hash, generate_password_hash

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# Add these lines at the top of your app.py after creating the Flask app
from werkzeug.middleware.proxy_fix import ProxyFix

# Make Flask work behind proxy (like ngrok) correctly
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Add this configuration to your app
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Initialize database
init_db()

# Instagram OAuth Configuration
INSTAGRAM_CLIENT_ID = os.getenv('INSTAGRAM_CLIENT_ID')
INSTAGRAM_CLIENT_SECRET = os.getenv('INSTAGRAM_CLIENT_SECRET')
REDIRECT_URI = os.getenv('INSTAGRAM_REDIRECT_URI2')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

# Set up logging
""" logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("facebook_urls.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('facebook_debug') """

# Add context processor to provide Instagram account info to all templates
@app.context_processor
def inject_account_info():
    instagram_username = None
    whatsapp_connected = False
    
    # Get Instagram info if available
    if 'access_token' in session and 'instagram_account_id' in session:
        access_token = session['access_token']
        account_info = get_account_info(access_token)
        if account_info and 'instagram_business_account' in account_info:
            instagram_username = account_info['instagram_business_account'].get('username')
    
    # Check if WhatsApp is connected
    if session.get('whatsapp_connected'):
        whatsapp_connected = True
    
    return {
        'instagram_username': instagram_username,
        'whatsapp_connected': whatsapp_connected
    }

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes for authentication
@app.route('/instagram-login')
@login_required
def instagram_login():
    return render_template('instagram-login.html')

# Add the login route (modified to support our basic auth)
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Very simple hardcoded credentials for demo purposes
        if username == 'test' and password == 'test1234!':
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
            
    return render_template('login.html', error=error)

# Add the logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return render_template('logout.html')

# Replace the existing index route
@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/auth')
def auth():
    scopes = ['instagram_business_manage_messages', 'instagram_business_basic']
    instagram_auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?client_id={INSTAGRAM_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={','.join(scopes)}"
        f"&response_type=code"
    )
    print("Instagram auth URL:", instagram_auth_url)
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
                business_id=ig_account_id,
                access_token=long_lived_token['access_token'],
                platform='instagram',
                expires_at=datetime.now() + timedelta(days=60)
            )
            print(f"Stored token for Instagram account: {ig_account_id}")
            session['instagram_account_id'] = ig_account_id
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Token exchange error: {e}")
        return f'Authentication failed: {str(e)}', 400

# Token exchange functions
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
    
def exchange_code_for_token(code):
    print("Exchanging code:", code)
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
    print ("Converting to long-lived token:", short_lived_token)
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

# Dashboard routes

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# HTMX partial routes for dynamic updates
@app.route('/users/<status>')
@app.route('/users/<status>/<platform>')
@login_required
def get_users(status, platform='all'):
    """Get users filtered by status and optionally by platform"""
    if platform == 'all':
        users = get_users_by_status(status.lower())
    else:
        users = get_users_by_status_and_platform(status.lower(), platform)
    
    # Pass the current filters to maintain state
    return render_template('partials/user_list.html', 
                          users=users, 
                          status=status.lower(),
                          status_filter=status.lower())

@app.route('/conversation/<sender_id>')
@login_required
def get_conversation(sender_id):
    """Get conversation with a specific user"""
    user_info = get_user_info(sender_id)
    messages = get_user_messages(sender_id)
    status = get_conversation_status(sender_id)
    return render_template('partials/conversation.html', 
                          messages=messages, 
                          user_info=user_info, 
                          sender_id=sender_id,
                          status=status)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    """Send message to user via appropriate platform"""
    sender_id = request.form.get('sender_id')
    message = request.form.get('message')
    platform = request.form.get('platform', 'instagram')  # Default to Instagram if not specified
    
    if not sender_id or not message:
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Get appropriate token and business ID
    success = False
    
    if platform == 'whatsapp':
        # Get WhatsApp credentials
        access_token = os.getenv('WA_META_APP_ACCESS_TOKEN')
        phone_number_id = os.getenv('WA_PHONE_NUMBER_ID')
        
        # Initialize WhatsApp API
        whatsapp = WhatsAppAPI(access_token, phone_number_id)
        
        # Send message
        result = whatsapp.send_message(sender_id, message)
        success = bool(result)
    else:
        # Instagram messaging
        access_token = session.get('access_token', os.getenv('INSTAGRAM_PAGE_ACCESS_TOKEN'))
        ig_user_id = session.get('instagram_account_id', os.getenv('INSTAGRAM_BUSINESS_ID'))
        
        # Initialize API
        instagram = InstagramAPI(access_token, ig_user_id)
        
        # Send message
        result = instagram.send_message(sender_id, message)
        success = bool(result)
    
    if success:
        # Save to database with correct platform
        save_message(sender_id, message, is_from_me=True, channel=platform)
        
        # Return updated conversation
        return get_conversation(sender_id)
    
    return jsonify({"error": f"Failed to send message via {platform}"}), 500


@app.route('/privacy-policy')
def privacy_policy():
    """Display the privacy policy page"""
    now = datetime.now()
    return render_template('privacy_policy.html', now=now)

@app.route('/set_assistant_mode', methods=['POST'])
@login_required
def set_assistant_mode():
    """Switch conversation back to AI assistant mode"""
    sender_id = request.form.get('sender_id')
    platform = request.form.get('platform', 'instagram')
    
    if not sender_id:
        return jsonify({"error": "Missing sender ID"}), 400
    
    # Set conversation back to assistant mode
    set_conversation_to_assistant(sender_id)
    
    # Send notification message
    notification = "You are now speaking with our AI assistant again."
    
    if platform == 'whatsapp':
        # WhatsApp notification
        access_token = os.getenv('WA_META_APP_ACCESS_TOKEN')
        phone_number_id = os.getenv('WA_PHONE_NUMBER_ID')
        whatsapp = WhatsAppAPI(access_token, phone_number_id)
        result = whatsapp.send_message(sender_id, notification)
    else:
        # Instagram notification
        access_token = session.get('access_token', os.getenv('INSTAGRAM_PAGE_ACCESS_TOKEN'))
        ig_user_id = session.get('instagram_account_id', os.getenv('INSTAGRAM_BUSINESS_ID'))
        instagram = InstagramAPI(access_token, ig_user_id)
        result = instagram.send_message(sender_id, notification)
    
    # Save notification in database
    save_message(sender_id, notification, is_from_me=True, channel=platform)
    
    # Return updated conversation
    return get_conversation(sender_id)

# Webhook handler for Instagram
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
                        stored_token = get_auth_token(recipient_id, platform='instagram')

                        print(f"Stored token for {recipient_id}: {stored_token}")
                        
                        if stored_token and stored_token.get('access_token'):
                            token_to_use = stored_token['access_token']
                        elif 'access_token' in session:
                            token_to_use = session['access_token']
                        else:
                            token_to_use = os.getenv('INSTAGRAM_PAGE_ACCESS_TOKEN')

                        if not token_to_use:
                            print("No valid token found")
                            return 'No valid token found', 400
                            
                        # Handle message with Instagram handler
                        try:
                            # Create handler without proxies
                            handler = InstagramMessageHandler(token_to_use, recipient_id)
                            if handler.handle_incoming_message(sender_id, text):
                                return 'EVENT_RECEIVED'
                            else:
                                return 'Failed to process message', 400
                        except Exception as e:
                            print(f"Error in webhook handler: {str(e)}")
                            print(f"Error type: {type(e)}")
                            # Log additional error information
                            import traceback
                            print(traceback.format_exc())
                            return Response('Bad Request', status=400)
                        
            return 'EVENT_RECEIVED'
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return Response('Bad Request', status=400)

# Add WhatsApp webhook route
@app.route('/whatsapp-webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        # Verification request from Meta
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        # Verify using the same token as Instagram (or use a separate one if needed)
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("WHATSAPP_WEBHOOK_VERIFIED")
            return challenge
        
        return Response('Forbidden', status=403)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.data.decode('utf-8'))
            print("Received WhatsApp webhook data:", data)
            
            # Check if this is a valid WhatsApp message
            if is_valid_whatsapp_message(data):
                entry = data['entry'][0]
                changes = entry.get('changes', [{}])[0]
                value = changes.get('value', {})
                
                # Get messages array
                messages = value.get('messages', [])
                if not messages:
                    return 'EVENT_RECEIVED'
                
                # Process first message
                message = messages[0]
                sender_id = message.get('from')
                message_id = message.get('id')
                timestamp = message.get('timestamp')
                
                # Process different message types
                if 'text' in message:
                    # Text message
                    message_text = message['text']['body']
                    process_whatsapp_message(sender_id, message_text, 'text')
                elif 'audio' in message:
                    # Audio message - we can extend to handle these later
                    # For now, acknowledge receipt
                    pass
                elif 'image' in message:
                    # Image message - we can extend to handle these later
                    pass
                
                return 'EVENT_RECEIVED'
            
            return 'EVENT_RECEIVED'
        except Exception as e:
            print(f"Error processing WhatsApp webhook: {e}")
            return Response('Bad Request', status=400)

# Helper functions for WhatsApp webhook
def is_valid_whatsapp_message(data):
    """Check if the incoming webhook event is a valid WhatsApp message"""
    return (
        data.get('object') == 'whatsapp_business_account' and
        data.get('entry') and
        len(data['entry']) > 0 and
        data['entry'][0].get('changes') and
        data['entry'][0]['changes'][0].get('value') and
        data['entry'][0]['changes'][0]['value'].get('messages')
    )

def process_whatsapp_message(sender_id, message_text, message_type='text'):
    """Process an incoming WhatsApp message"""
    try:
        # Get WhatsApp credentials
        phone_number_id = os.getenv('WA_PHONE_NUMBER_ID')
        access_token = os.getenv('WA_META_APP_ACCESS_TOKEN')
        
        if not phone_number_id or not access_token:
            print("Missing WhatsApp credentials")
            return False
        
        # Create WhatsApp message handler
        handler = WhatsAppMessageHandler(access_token, phone_number_id)
        
        # Handle the message
        result = handler.handle_incoming_message(sender_id, message_text, message_type)
        return result
    except Exception as e:
        print(f"Error processing WhatsApp message: {e}")
        return False

# Add missing function
def set_conversation_to_assistant(sender_id):
    """Switch conversation back to assistant mode and save status change"""
    try:
        # Use the existing function from database module
        return set_conversation_status(sender_id, 'assistant')
    except Exception as e:
        print("LOGGER" +f"Error switching conversation status: {e}")
        return False

# Add missing function for token refreshing that exists in main.py
@app.route('/refresh_token')
@login_required
def refresh_token_route():
    """Refresh the Instagram access token"""
    if 'access_token' not in session:
        return jsonify({"error": "No token in session"}), 401
        
    try:
        response = requests.get('https://graph.instagram.com/refresh_access_token', params={
            'grant_type': 'ig_refresh_token',
            'access_token': session['access_token']
        })
        
        if response.status_code == 200:
            data = response.json()
            session['access_token'] = data['access_token']
            session['token_expires'] = (datetime.now() + timedelta(seconds=data['expires_in'])).strftime('%Y-%m-%d %H:%M:%S')
            
            # Also update in database if we have the account ID
            if 'instagram_account_id' in session:
                save_auth_token(
                    business_id=session['instagram_account_id'],
                    access_token=data['access_token'],
                    platform='instagram',
                    expires_at=datetime.now() + timedelta(seconds=data['expires_in'])
                )
                
            return jsonify({"success": True, "expires_in": data['expires_in']})
        
        return jsonify({"error": f"Failed to refresh token: {response.text}"}), 400
    except Exception as e:
        print("LOGGER" +f"Error refreshing token: {e}")
        return jsonify({"error": str(e)}), 500

# Add the deauthorize and delete-data routes from main.py
@app.route('/deauthorize', methods=['POST'])
def deauthorize():
    try:
        data = json.loads(request.data.decode('utf-8'))
        user_id = data.get('signed_request', {}).get('user_id')
        
        if user_id:
            # Clean up user data from database
            print("LOGGER" +f"Deauthorized user: {user_id}")
            
        return Response('', status=200)
    except Exception as e:
        print("LOGGER" +f"Deauthorization error: {e}")
        return Response('Bad Request', status=400)

@app.route('/delete-data', methods=['POST'])
def delete_data():
    try:
        data = json.loads(request.data.decode('utf-8'))
        user_id = data.get('signed_request', {}).get('user_id')
        
        if user_id:
            # Implement permanent data deletion for the user
            print("LOGGER" +f"Data deletion request for user: {user_id}")
            
        return Response('', status=200)
    except Exception as e:
        print("LOGGER" +f"Data deletion error: {e}")
        return Response('Bad Request', status=400)

# Update manual token endpoint
@app.route('/save_manual_token', methods=['POST'])
def save_manual_token():
    """Save manually entered token and business ID"""
    access_token = request.form.get('access_token')
    business_id = request.form.get('business_id')
    platform = request.form.get('platform', 'instagram')
    
    if not access_token or not business_id:
        return render_template('error.html', message="Both access token and business ID are required")
    
    # Save to session
    session['access_token'] = access_token
    if platform == 'instagram':
        session['instagram_account_id'] = business_id
    
    # Save to database
    save_auth_token(business_id=business_id, access_token=access_token, platform=platform)
    
    return redirect(url_for('dashboard'))

# WhatsApp routes
@app.route('/whatsapp-signup')
@login_required
def whatsapp_signup():
    """WhatsApp embedded sign-up page"""
    # Configuration for WhatsApp sign-up
    app_id = os.getenv('WA_META_APP_ID')
    config_id = os.getenv('WA_CONFIG_ID')
    
    # Log the current URL for debugging
    print("LOGGER" +f"Current whatsapp-signup URL: {request.url}")
    print("LOGGER" +f"Request root URL: {request.url_root}")
    
    # No longer use url_for to ensure consistency
    # Create the redirect URLs manually to match the format in fallback_redirect_uri
    base_url = request.url_root.rstrip('/')
    callback_url = f"{base_url}/whatsapp-signup/callback"
    success_url = f"{base_url}/whatsapp-success"
    error_url = f"{base_url}/whatsapp-error"
    
    # Ensure HTTPS
    if callback_url.startswith('http:'):
        callback_url = 'https:' + callback_url[5:]
    if success_url.startswith('http:'):
        success_url = 'https:' + success_url[5:]
    if error_url.startswith('http:'):
        error_url = 'https:' + error_url[5:]
    
    print("LOGGER" +f"Webhook signup URLs - Success: {success_url}, Error: {error_url}, Callback: {callback_url}")
    
    return render_template('whatsapp_signup.html', 
                          app_id=app_id,
                          config_id=config_id,
                          success_url=success_url,
                          error_url=error_url,
                          callback_url=callback_url)

@app.route('/whatsapp-signup/callback', methods=['POST'])
def whatsapp_signup_callback():
    """Handle WhatsApp sign-up callback data with improved URI handling"""
    data = request.json
    print("LOGGER" +f"WhatsApp signup callback data: {data}")
    
    try:
        # Extract data from request
        code = data.get('code')
        waba_id = data.get('wabaId')
        phone_number_id = data.get('phoneNumberId')
        client_redirect_uri = data.get('redirectUri')
        
        print("LOGGER" +f"Client reported redirect URI: '{client_redirect_uri}'")
        
        # Validate inputs
        if not code:
            return jsonify({'success': False, 'error': 'Missing authorization code'}), 400
        
        # Try with client-provided redirect URI first if available
        if client_redirect_uri:
            print("LOGGER" +f"Trying with client-provided URI first: {client_redirect_uri}")
            # Rest of the code for token exchange...
        
        # If that doesn't work or no client URI provided, use our calculated one
        print("LOGGER" +f"Attempting code exchange")
        system_user_id, system_token = exchange_code_for_wa_token(code)
        
        # ...existing code...

        return jsonify({'success': True})
    except Exception as e:
        print("LOGGER" +f"Error processing WhatsApp sign-up: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def exchange_code_for_wa_token(code):
    """Exchange code for WhatsApp system user token"""
    try:
        # Get Meta app access token from environment
        app_id = os.getenv('WA_META_APP_ID')
        app_secret = os.getenv('WA_APP_CLIENT_SECRET', '')
        
        # IMPORTANT FIX: Manually create the exact same redirect URI with consistent trailing slash handling
        # Facebook uses /whatsapp-signup WITHOUT trailing slash
        base_url = request.url_root.rstrip('/')  # Remove any trailing slash
        redirect_uri = f"{base_url}/whatsapp-signup"  # Add path without trailing slash
        
        # Make sure we're using HTTPS
        if redirect_uri.startswith('http:'):
            redirect_uri = 'https:' + redirect_uri[5:]
            
        print("LOGGER" +f"EXACT Redirect URI being used: '{redirect_uri}'")
        
        # Log the fallback URI from the actual Facebook URL for comparison
        print("LOGGER" +f"Expected fallback URI: 'https://steady-perch-evidently.ngrok-free.app/whatsapp-signup'")

        # Exchange code for access token using Meta Graph API
        response = requests.get(
            'https://graph.facebook.com/v22.0/oauth/access_token',
            params={
                'client_id': app_id,
                'client_secret': app_secret,
                'redirect_uri': redirect_uri,
                'code': code
            }
        )
        
        # Log complete request for debugging
        print("LOGGER" +f"Token exchange request URL: {response.request.url}")
        
        if response.status_code != 200:
            print("LOGGER" +f"Error exchanging code: {response.text}")
            return None, None
            
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            print("LOGGER" +"No access token in response")
            return None, None
        
        # Get system user ID from the token
        user_response = requests.get(
            'https://graph.facebook.com/v22.0/me',
            params={
                'access_token': access_token,
                'fields': 'id,name'
            }
        )
        
        if user_response.status_code != 200:
            print("LOGGER" +f"Error getting user info: {user_response.text}")
            return None, None
            
        user_data = user_response.json()
        system_user_id = user_data.get('id')
        
        if not system_user_id:
            print("LOGGER" +"No system user ID in response")
            return None, None
            
        return system_user_id, access_token
        
    except Exception as e:
        print("LOGGER" +f"Exception in exchange_code_for_wa_token: {str(e)}")
        return None, None

def get_whatsapp_business_info(system_user_id, access_token):
    """Get WhatsApp Business Account info using system user token"""
    try:
        # Query system user accounts to get WABA info
        response = requests.get(
            f"https://graph.facebook.com/v22.0/{system_user_id}/accounts",
            params={
                'access_token': access_token
            }
        )
        
        if response.status_code != 200:
            print("LOGGER" +f"Error getting accounts: {response.text}")
            return None
            
        accounts_data = response.json()
        
        # Find WhatsApp Business Account
        for account in accounts_data.get('data', []):
            if account.get('category') == 'WhatsApp Business Account':
                waba_id = account.get('id')
                
                # Get phone number ID
                phone_response = requests.get(
                    f"https://graph.facebook.com/v22.0/{waba_id}/phone_numbers",
                    params={
                        'access_token': access_token
                    }
                )
                
                if phone_response.status_code == 200:
                    phone_data = phone_response.json()
                    if phone_data.get('data') and len(phone_data['data']) > 0:
                        phone_number_id = phone_data['data'][0].get('id')
                        return {
                            'wabaId': waba_id,
                            'phoneNumberId': phone_number_id
                        }
        
        return None
        
    except Exception as e:
        print("LOGGER" +f"Exception in get_whatsapp_business_info: {str(e)}")
        return None

@app.route('/whatsapp-success')
def whatsapp_success():
    """Success page after WhatsApp sign-up"""
    # Check for any code parameter that might be passed
    code = request.args.get('code')
    
    # If there's a code and we don't have WABA info yet, we can try to use it
    if code and not session.get('whatsapp_connected'):
        try:
            # Try to exchange the code for a token
            system_user_id, access_token = exchange_code_for_wa_token(code)
            phone_number_id = waba_info.get('phoneNumberId')
            
            if system_user_id and access_token:
                # Try to get WhatsApp Business info
                waba_info = get_whatsapp_business_info(system_user_id, access_token)
                
                if waba_info:
                    # Save the WhatsApp business info
                    save_whatsapp_business(
                        waba_id=waba_info.get('wabaId'),
                        phone_number_id=phone_number_id,
                        system_user_id=system_user_id,
                        access_token=access_token
                    )
                    # Mark as connected in session
                    session['whatsapp_connected'] = True
                
                return render_template('whatsapp_success.html', phone_number_id=phone_number_id)
            
        except Exception as e:
            print("LOGGER WARNING" +f"Could not process code on success page: {e}")
            # We'll still show the success page even if code processing fails
    
    # FOR TESTING, we can simulate a successful connection
    session['whatsapp_connected'] = True
    
    return render_template('whatsapp_success.html')

@app.route('/whatsapp-error')
def whatsapp_error():
    """Error page for WhatsApp sign-up"""
    error = request.args.get('error', 'An unknown error occurred')
    return render_template('error.html', message=f"WhatsApp registration error: {error}")

# Helper functions for WhatsApp integration
def get_whatsapp_system_user_token(system_user_id):
    """Get permanent access token for WhatsApp system user"""
    try:
        # Fetch token using Meta Graph API
        response = requests.get(
            f"https://graph.facebook.com/v17.0/{system_user_id}",
            params={
                'access_token': os.getenv('WA_META_APP_ACCESS_TOKEN'),
                'fields': 'access_token'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token')
        
        print("LOGGER" +f"Error getting system user token: {response.text}")
        return None
        
    except Exception as e:
        print("LOGGER" +f"Exception getting system user token: {e}")
        return None

def save_whatsapp_business(waba_id, phone_number_id, system_user_id, access_token):
    """Save WhatsApp business information to database"""
    try:
        # Save token with WhatsApp-specific fields
        save_auth_token(
            business_id=waba_id,
            platform='whatsapp',
            access_token=access_token,
            phone_number_id=phone_number_id,
            waba_id=waba_id,
            system_user_id=system_user_id
        )
        
        return True
    except Exception as e:
        print("LOGGER" +f"Error saving WhatsApp business: {e}")
        return False

@app.before_request
def log_request_info():
    """Log all request details to help debug Facebook redirects"""
    g.request_start_time = time.time()
    
    # Log all request details
    print("LOGGER INFO" +f"Request URL: {request.url}")
    print("LOGGER INFO" +f"Request Method: {request.method}")
    print("LOGGER INFO" +f"Request Headers: {dict(request.headers)}")
    print("LOGGER INFO" +f"Request Args: {dict(request.args)}")
    
    if request.url.endswith('whatsapp-success') or 'callback' in request.url:
        print("LOGGER INFO" +f"OAUTH REDIRECT URL DETECTED: {request.url}")
        print("LOGGER INFO" +f"Query Parameters: {dict(request.args)}")

@app.after_request
def log_response_info(response):
    """Log response details"""
    if hasattr(g, 'request_start_time'):
        duration = time.time() - g.request_start_time
        print("LOGGER INFO" +f"Request duration: {duration:.2f}s")
        print("LOGGER INFO" +f"Response Status: {response.status_code}")
        
    return response

# Add a wildcard route to catch any Facebook redirects
@app.route('/<path:path>')
def catch_all(path):
    """Catch-all route to log Facebook redirects"""
    print("LOGGER WARNING" +f"Unhandled path accessed: /{path}")
    print("LOGGER WARNING" +f"Full URL: {request.url}")
    print("LOGGER WARNING" +f"Query Parameters: {dict(request.args)}")
    
    # If this seems like an OAuth redirect, log it clearly
    if 'code' in request.args:
        print("LOGGER WARNING" +f"POTENTIAL MISSED OAUTH REDIRECT: {request.url}")
    
    # Redirect to whatsapp success page if it seems like an OAuth redirect
    if 'code' in request.args:
        return redirect(url_for('whatsapp_success', code=request.args.get('code')))
    
    return "Page not found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7777))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'True').lower() == 'true')