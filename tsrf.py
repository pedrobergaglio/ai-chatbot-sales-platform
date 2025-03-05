from instagram_api import InstagramAPI
from database import save_message, save_user_info, set_conversation_status
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
            if self.needs_human_help(message_text):
                set_conversation_status(sender_id, 'human')
                return "I understand you'd like to speak with a human representative. I'm transferring your conversation to our support team. Please wait for a human agent to respond."
            
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
            
            # Check for human help request
            needs_human = self.needs_human_help(message_text)
            
            # Save received message with human help flag if needed
            save_message(sender_id, message_text, is_from_me=False, human_help_flag=needs_human)
            print(f"Saved incoming message (human_help_flag: {needs_human})")
            
            # Try to get user profile info but don't fail if unavailable
            user_info = self.instagram.get_user_info(sender_id)
            if user_info:
                save_user_info(
                    sender_id=sender_id,
                    username=user_info.get('username')
                )
            
            # Get AI response
            response_text = self.agent_response(message_text, sender_id)
            
            # If human help was requested, save the response but don't send it
            if needs_human:
                save_message(sender_id, response_text, is_from_me=True, human_help_flag=True)
                print("Human help requested - message saved but not sent")
                return True
            
            # Send response for non-human help cases
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
            return False
        finally:
            print(f"=== Message Processing Complete ===\n")
