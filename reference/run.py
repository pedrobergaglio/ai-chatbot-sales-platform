import subprocess
import sys
import os
from threading import Thread
import time
import signal
import platform

def is_mac():
    return platform.system() == 'Darwin'

def setup_nginx():
    """Setup Nginx configuration"""
    nginx_path = '/opt/homebrew/etc/nginx' if is_mac() else '/etc/nginx'
    conf_path = os.path.join(os.path.dirname(__file__), 'nginx', 'instagram-chat.conf')
    
    try:
        # Create symbolic link to Nginx config
        if is_mac():
            subprocess.run(['brew', 'services', 'start', 'nginx'])
        else:
            subprocess.run(['sudo', 'systemctl', 'start', 'nginx'])
            
        # Link our configuration
        target_path = os.path.join(nginx_path, 'servers', 'instagram-chat.conf')
        if not os.path.exists(target_path):
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            subprocess.run(['ln', '-sf', conf_path, target_path])
        
        # Reload Nginx
        if is_mac():
            subprocess.run(['brew', 'services', 'reload', 'nginx'])
        else:
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'])
            
        print("✅ Nginx configured successfully")
    except Exception as e:
        print(f"❌ Error configuring Nginx: {e}")
        sys.exit(1)

def run_flask():
    """Run Flask application"""
    subprocess.run([sys.executable, "main.py"])

def run_streamlit():
    """Run Streamlit dashboard"""
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "dashboard.py",
        "--server.headless", "true",
        "--server.baseUrlPath", "dashboard",
        "--server.address", "0.0.0.0",
        "--server.port", "8501",
        "--browser.serverAddress", "b4fvhl4w-8501.brs.devtunnels.ms",
        "--server.runOnSave", "true"
    ])

def main():
    print("🚀 Starting Instagram Chat Platform...")
    
    # Setup Nginx first
    setup_nginx()
    
    # Start services in separate threads
    flask_thread = Thread(target=run_flask)
    streamlit_thread = Thread(target=run_streamlit)
    
    try:
        flask_thread.start()
        print("✅ Flask server started on port 7777")
        
        time.sleep(2)  # Wait for Flask to start
        
        streamlit_thread.start()
        print("✅ Streamlit dashboard started on port 8501")
        
        print("\n🌟 Application is running!")
        print("Main application: http://localhost")
        print("Dashboard: http://localhost/dashboard")
        
        # Keep main thread alive and handle keyboard interrupt
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        # Cleanup Nginx
        if is_mac():
            subprocess.run(['brew', 'services', 'stop', 'nginx'])
        else:
            subprocess.run(['sudo', 'systemctl', 'stop', 'nginx'])
        
        # Force exit threads
        os._exit(0)

if __name__ == "__main__":
    main()
