from openai import OpenAI
import os
from dotenv import load_dotenv
from database import get_db
import httpx

load_dotenv()

class ThreadManager:
    def __init__(self):
        # Initialize OpenAI client without using httpx directly
        try:
            # Simple initialization without custom client
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Print httpx version for debugging
            print(f"Using httpx version: {httpx.__version__}")
            
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            # Emergency fallback
            import openai
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.client = openai
        
        self.system_message = """You are a professional sales consultant for 'Soluciones Sauco', 
        a software company specializing in digital transformation solutions. 

        Our main services include:
        - Custom Enterprise Resource Planning (ERP) Systems
        - Business Intelligence and Analytics Solutions
        - Cloud Migration Services
        - Digital Workflow Automation
        - Legacy System Modernization
        - Custom Software Development
        - Mobile App Development
        - IT Infrastructure Optimization
        - Cybersecurity Solutions
        
        Guidelines:
        1. Always maintain a professional and courteous tone
        2. Only discuss our software and digital transformation services
        3. Do not discuss hardware, physical products, or non-IT related topics
        4. Never quote specific prices without verification
        5. If asked about project timelines or costs, explain that each solution is customized and requires a detailed assessment
        6. Focus on understanding the client's business challenges first
        7. Emphasize our expertise in creating tailored solutions
        8. For technical specifications or precise quotes, offer to arrange a meeting with our solutions architects
        9. When the conversation requires human expertise or if the user specifically requests human assistance, 
           respond with 'HUMAN HELP' in your message
        10. Use less than 400 chars in each message to ensure clear and concise communication and avoid truncation
        11. Dont use * or _ for formatting, as it may not render correctly in all messaging platforms
        
        Keep responses concise, friendly, and focused on how we can help businesses modernize their operations through technology."""
        self._init_db()
    
    def _init_db(self):
        """Initialize conversation storage"""
        with get_db() as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    user_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    role TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.commit()
    
    def _get_conversation_history(self, user_id, limit=10):
        """Get recent conversation history for the user"""
        with get_db() as db:
            messages = db.execute('''
                SELECT role, message FROM conversations 
                WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, limit)).fetchall()
            return list(reversed([dict(m) for m in messages]))
    
    def _save_message(self, user_id, message, role):
        """Save a message to the conversation history"""
        with get_db() as db:
            db.execute('''
                INSERT INTO conversations (user_id, message, role)
                VALUES (?, ?, ?)
            ''', (user_id, message, role))
            db.commit()
    
    def get_response(self, user_id, message):
        """Get response using chat completion"""
        try:
            print(f"\n=== OpenAI Interaction Start ===")
            print(f"Processing message from user {user_id}: {message[:50]}...")
            
            # Save user message
            self._save_message(user_id, message, 'user')
            
            # Get conversation history
            history = self._get_conversation_history(user_id)
            print(f"Retrieved {len(history)} previous messages from history")
            
            # Prepare messages for API
            messages = [
                {"role": "system", "content": self.system_message}
            ]
            
            # Add conversation history
            for msg in history:
                messages.append({
                    "role": msg['role'],
                    "content": msg['message']
                })
            
            print(f"Sending request to OpenAI with {len(messages)} messages")
            print(f"System message: {self.system_message[:100]}...")
            
            # Get completion
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=messages,
                temperature=0,
                max_tokens=100  # Keep responses concise
            )
            
            # Save and return assistant's response
            assistant_message = response.choices[0].message.content
            print(f"Received response from OpenAI: {assistant_message}")
            
            self._save_message(user_id, assistant_message, 'assistant')
            print(f"=== OpenAI Interaction Complete ===\n")
            
            return assistant_message
            
        except Exception as e:
            print(f"=== OpenAI Error ===")
            print(f"Error getting response: {str(e)}")
            print(f"Error type: {type(e)}")
            print(f"=== Error Details End ===\n")
            return "Lo siento, estoy teniendo problemas para procesar tu mensaje. ¿Podrías intentarlo de nuevo?"
