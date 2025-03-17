import os
from dotenv import load_dotenv
from thread_manager import ThreadManager

load_dotenv()

def test_thread_manager_init():
    """Test if ThreadManager can be initialized without proxy errors"""
    print("Testing ThreadManager initialization...")
    
    try:
        thread_manager = ThreadManager()
        print("✅ SUCCESS: ThreadManager initialized successfully!")
        
        # Test a simple completion to verify full functionality
        try:
            test_response = thread_manager.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=10
            )
            print(f"✅ API test successful! Response: {test_response.choices[0].message.content}")
        except Exception as api_error:
            print(f"❌ API test failed: {str(api_error)}")
        
    except Exception as e:
        print(f"❌ FAILED: Error initializing ThreadManager: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_thread_manager_init()
