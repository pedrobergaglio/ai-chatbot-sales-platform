from instagram_api import InstagramAPI
from database import save_message, save_user_info, set_conversation_status
from thread_manager import ThreadManager

class MessageHandler:
    def __init__(self, access_token, ig_user_id):
        self.instagram = InstagramAPI(access_token, ig_user_id)
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
                set_conversation_status(sender_id, 'assistant')
                print(f"Stored user info and conversation status: {user_info}")
            else:
                print(f"Proceeding without user profile info")
            
            # Get AI response first
            response_text = self.agent_response(message_text, sender_id)
            needs_human = self.needs_human_help(response_text)
            
            # Save received message with human help flag if needed
            save_message(sender_id, message_text, is_from_me=False, human_help_flag=needs_human)
            
            # If human help was requested, save the response but don't send it
            if needs_human:
                save_message(sender_id, response_text, is_from_me=True, human_help_flag=True)
                print("AI requested human help - message saved but not sent")
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
