from instagram_api import InstagramAPI
from database import save_message, save_user_info
from thread_manager import ThreadManager

class MessageHandler:
    def __init__(self, access_token, ig_user_id):
        self.instagram = InstagramAPI(access_token, ig_user_id)
        self.thread_manager = ThreadManager()

        # Keywords that trigger human help
        self.human_help_triggers = [
            'speak to a human',
            'talk to a representative',
            'speak with someone',
            'talk to a person',
            'human support',
            'real person',
            'agent',
            'representative',
            'speak to someone',
            'human agent',
            'customer service'
        ]

    def needs_human_help(self, message_text):
        """Check if the message indicates a need for human help"""
        message_lower = message_text.lower()
        return any(trigger in message_lower for trigger in self.human_help_triggers)
    
    def agent_response(self, message_text, sender_id):
        """Get response from OpenAI assistant"""
        try:
            return self.thread_manager.get_response(sender_id, message_text)
        except Exception as e:
            print(f"Error getting agent response: {e}")
            return "I apologize, I'm having trouble processing your message."
    
    def handle_incoming_message(self, sender_id, message_text):
        """Process incoming message and return appropriate response"""
        try:
            print(f"\n=== Processing Message ===")
            print(f"Sender ID: {sender_id}")
            print(f"Message: {message_text}")
            
            # Try to get user profile info but don't fail if unavailable
            user_info = self.instagram.get_user_info(sender_id)
            if user_info:
                save_user_info(
                    sender_id=sender_id,
                    username=user_info.get('username')
                )
                print(f"Stored user info: {user_info}")
            else:
                print(f"Proceeding without user profile info")

            # Save received message
            save_message(sender_id, message_text, is_from_me=False)
            print(f"Saved incoming message")
            
            # Get AI response
            print("Requesting AI response...")
            response_text = self.agent_response(message_text, sender_id)
            print(f"AI response received: {response_text[:100]}...")
            
            # Send response
            print("Sending response to Instagram...")
            result = self.instagram.send_message(sender_id, response_text)
            
            if result:
                save_message(sender_id, response_text, is_from_me=True)
                print("Response sent and saved successfully")
                return True
            
            print("Failed to send response")
            return False
            
        except Exception as e:
            print(f"=== Error in handle_incoming_message ===")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e)}")
            return False
        finally:
            print(f"=== Message Processing Complete ===\n")
