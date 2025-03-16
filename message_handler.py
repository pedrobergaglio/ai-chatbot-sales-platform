from instagram_api import InstagramAPI
from whatsapp_api import WhatsAppAPI
from database import save_message, save_user_info, set_conversation_status
from thread_manager import ThreadManager

class BaseMessageHandler:
    """Base class for message handling across platforms"""
    
    def __init__(self):
        self.thread_manager = ThreadManager()
    
    def needs_human_help(self, response_text):
        """Check if the AI response indicates need for human help"""
        return "HUMAN HELP" in response_text.upper()
    
    def agent_response(self, message_text, sender_id):
        """Get response from OpenAI assistant"""
        try:
            response = self.thread_manager.get_response(sender_id, message_text)
            
            # Check if AI requested human help
            if self.needs_human_help(response):
                set_conversation_status(sender_id, 'human')
                # Clean response and add human transfer message
                return "I'm transferring you to a human representative who will assist you further. Please wait for their response."
            
            return response
        except Exception as e:
            print(f"Error getting agent response: {e}")
            return "I apologize, I'm having trouble processing your message."
    
    def handle_incoming_message(self, sender_id, message_text):
        """Process incoming message - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement this method")
        
    def _save_received_message(self, sender_id, message_text, needs_human=False, channel='instagram'):
        """Save message received from user"""
        save_message(sender_id, message_text, is_from_me=False, human_help_flag=needs_human, channel=channel)
    
    def _save_sent_message(self, sender_id, response_text, needs_human=False, channel='instagram'):
        """Save message sent to user"""
        save_message(sender_id, response_text, is_from_me=True, human_help_flag=needs_human, channel=channel)


class InstagramMessageHandler(BaseMessageHandler):
    """Instagram-specific message handler"""
    
    def __init__(self, access_token, ig_user_id, **kwargs):
        # Initialize BaseMessageHandler but ignore extra kwargs
        super().__init__()
        # Create Instagram API without passing unexpected kwargs
        self.instagram = InstagramAPI(access_token, ig_user_id)
        self.platform = 'instagram'
    
    def handle_incoming_message(self, sender_id, message_text):
        """Process incoming Instagram message"""
        try:
            print(f"\n=== Processing Instagram Message ===")
            print(f"Sender ID: {sender_id}")
            print(f"Message: {message_text}")

            # Try to get user profile info
            user_info = self.instagram.get_user_info(sender_id)
            if user_info:
                save_user_info(
                    sender_id=sender_id,
                    username=user_info.get('username'),
                    platform=self.platform
                )
                set_conversation_status(sender_id, 'assistant')
                print(f"Stored user info and conversation status: {user_info}")
            else:
                print(f"Proceeding without user profile info")
            
            # Get AI response first
            response_text = self.agent_response(message_text, sender_id)
            needs_human = self.needs_human_help(response_text)
            
            # Save received message
            self._save_received_message(sender_id, message_text, needs_human, self.platform)
            
            # If human help was requested, save the response but don't send it
            if needs_human:
                self._save_sent_message(sender_id, response_text, True, self.platform)
                print("AI requested human help - message saved but not sent")
                return True
            
            # Send response for non-human help cases
            result = self.instagram.send_message(sender_id, response_text)
            
            if result:
                self._save_sent_message(sender_id, response_text, False, self.platform)
                print("Response sent and saved successfully")
                return True
            
            print("Failed to send response")
            return False
            
        except Exception as e:
            print(f"=== Error in Instagram message handler ===")
            print(f"Error: {str(e)}")
            return False
        finally:
            print(f"=== Instagram Message Processing Complete ===\n")


class WhatsAppMessageHandler(BaseMessageHandler):
    """WhatsApp-specific message handler"""
    
    def __init__(self, access_token, phone_number_id):
        super().__init__()
        self.whatsapp = WhatsAppAPI(access_token, phone_number_id)
        self.platform = 'whatsapp'
    
    def handle_incoming_message(self, sender_id, message_text, message_type='text'):
        """Process incoming WhatsApp message"""
        try:
            print(f"\n=== Processing WhatsApp Message ===")
            print(f"Sender ID: {sender_id}")
            print(f"Message: {message_text}")
            
            # Save user info (phone number is the identifier in WhatsApp)
            # Normalize phone number by removing WhatsApp's default "+" prefix
            phone_number = sender_id.lstrip('+')
            save_user_info(
                sender_id=sender_id,
                phone_number=phone_number,
                platform=self.platform
            )
            
            # Set status to assistant by default
            set_conversation_status(sender_id, 'assistant')
            
            # Get AI response
            response_text = self.agent_response(message_text, sender_id)
            needs_human = self.needs_human_help(response_text)
            
            # Save received message
            self._save_received_message(sender_id, message_text, needs_human, self.platform)
            
            # If human help was requested, save the response but don't send it
            if needs_human:
                self._save_sent_message(sender_id, response_text, True, self.platform)
                print("AI requested human help - message saved but not sent")
                return True
            
            # Send response for non-human help cases
            result = self.whatsapp.send_message(sender_id, response_text)
            
            if result:
                self._save_sent_message(sender_id, response_text, False, self.platform)
                print("WhatsApp response sent and saved successfully")
                return True
            
            print("Failed to send WhatsApp response")
            return False
            
        except Exception as e:
            print(f"=== Error in WhatsApp message handler ===")
            print(f"Error: {str(e)}")
            return False
        finally:
            print(f"=== WhatsApp Message Processing Complete ===\n")


def create_message_handler(platform, access_token, business_id):
    """Factory function to create appropriate message handler based on platform"""
    if platform == 'instagram':
        return InstagramMessageHandler(access_token, business_id)
    elif platform == 'whatsapp':
        return WhatsAppMessageHandler(access_token, business_id)
    else:
        raise ValueError(f"Unsupported platform: {platform}")
