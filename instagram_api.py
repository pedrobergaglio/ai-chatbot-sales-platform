import requests
import os
from dotenv import load_dotenv

load_dotenv()

class InstagramAPI:
    def __init__(self, access_token, ig_user_id):
        self.access_token = access_token
        self.ig_user_id = str(ig_user_id).strip()  # Clean the ID
        self.api_version = 'v22.0'
        self.base_url = 'https://graph.instagram.com'

    def get_user_info(self, instagram_scoped_id):
        """Fetch Instagram user information using IGSID"""
        url = f"{self.base_url}/{self.api_version}/{instagram_scoped_id}"
        params = {
            'access_token': self.access_token,
            'fields': 'name,username,profile_pic,follower_count,is_user_follow_business,is_business_follow_user'
        }
        print(f"Requesting user info with URL: {url}")
        
        try:
            response = requests.get(url, params=params)
            print(f"User info response: {response.text}")
            
            # Handle case where content isn't available (no user consent yet)
            if response.status_code == 400 and "content isn't available" in response.text:
                print("User info not available - requires user consent")
                return None
                
            if response.status_code == 200:
                return response.json()
                
            print(f"Error getting user info: {response.status_code}")
            return None
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None

    def send_message(self, recipient_id, message_text):
        """Send message using Instagram Graph API"""
        url = f"{self.base_url}/{self.api_version}/{self.ig_user_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "recipient": {
                "id": str(recipient_id)
            },
            "message": {
                "text": message_text[:1000]  # Ensure message is within limits
            }
        }

        print(f"Sending message to {recipient_id}: {message_text[:100]}...")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()
            
            if response.status_code == 200:
                print(f"Message sent successfully to {recipient_id}")
                return response_data
            else:
                print(f"Error sending message: {response_data}")
                return None
                
        except Exception as e:
            print(f"Exception while sending message: {e}")
            return None