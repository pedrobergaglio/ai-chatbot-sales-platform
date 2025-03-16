import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

class WhatsAppAPI:
    """Client for WhatsApp Cloud API"""
    
    def __init__(self, access_token, phone_number_id):
        self.access_token = access_token
        self.phone_number_id = str(phone_number_id).strip()
        self.api_version = 'v22.0'  
        self.base_url = 'https://graph.facebook.com'
    
    def send_message(self, recipient_id, message_text):
        """Send text message to WhatsApp user"""

        if recipient_id.startswith('549'):
            # Eliminar el '9' del número de teléfono
            recipient_id = recipient_id[:2] + recipient_id[3:]

        print(f"Token: {self.access_token}")

        url = f"{self.base_url}/{self.api_version}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # WhatsApp Cloud API payload format
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "text": {
            "preview_url": False,
            "body": message_text[:4000]  # WhatsApp has a 4000 char limit
            }
        }
        
        print(f"Request1234 data: {data}, headers: {headers}, url: {url}")
        
        try:
            response = requests.post(url, json=data, headers=headers)
            
            # Debug response
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text[:200]}...")
            
            if response.status_code == 200:
                if response.text.strip():
                    try:
                        response_data = response.json()
                        return response_data
                    except json.JSONDecodeError as e:
                        print(f"JSON parse error: {e}")
                        return True if response.status_code == 200 else False
                else:
                    return True
            else:
                print(f"Error status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Exception while sending WhatsApp message: {e}")
            return False
    
    def send_media_message(self, recipient_id, media_type, media_url, caption=None):
        """Send media message to WhatsApp user"""
        url = f"{self.base_url}/{self.api_version}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Media message payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": media_type,  # image, audio, document, video
            media_type: {
                "link": media_url
            }
        }
        
        # Add caption if provided
        if caption and media_type in ['image', 'video', 'document']:
            payload[media_type]['caption'] = caption
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return response.status_code == 200
        except Exception as e:
            print(f"Exception while sending WhatsApp media: {e}")
            return False
    
    def get_user_info(self, phone_number):
        """WhatsApp doesn't provide user info API, so we store what we know"""
        # User info is managed internally through saves in the message handler
        return {
            'phone_number': phone_number
        }
