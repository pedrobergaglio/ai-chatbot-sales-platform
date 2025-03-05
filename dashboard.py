import streamlit as st
import sqlite3
from database import (
    get_unique_users, 
    get_user_messages, 
    get_user_info, get_users_by_status, 
    set_conversation_status, save_message)
from datetime import datetime
from time import sleep
import os
from dotenv import load_dotenv
from instagram_api import InstagramAPI

# Load environment variables
load_dotenv()

# Set base URL path for Streamlit
BASE_URL = "https://b4fvhl4w-7777.brs.devtunnels.ms"

# Set Streamlit page configuration
st.set_page_config(
    page_title="Instagram Chat Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Add base path to session state
if 'base_path' not in st.session_state:
    st.session_state['base_path'] = '/dashboard'

# Add base URL to session state
if 'base_url' not in st.session_state:
    st.session_state['base_url'] = BASE_URL

# Apply dark theme
st.markdown("""
    <style>
        .stApp {
            background-color: #1E1E1E;
            color: #FFFFFF;
        }
        .chat-message {
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            max-width: 70%;
        }
        .message-received {
            background-color: #2D2D2D;
            margin-right: 20%;
        }
        .message-sent {
            background-color: #0B5394;
            margin-left: 20%;
        }
        .timestamp {
            font-size: 0.8em;
            color: #888888;
        }
        /* Style the selectbox to look like our table */
        .stSelectbox [data-baseweb="select"] {
            background-color: transparent !important;
        }
        .stSelectbox div[role="listbox"] {
            background-color: #2D2D2D;
        }
        .stSelectbox div[role="option"] {
            padding: 8px 12px;
            border-bottom: 1px solid #333;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .stSelectbox div[role="option"]:hover {
            background-color: #3D3D3D;
        }
        .stSelectbox [aria-selected="true"] {
            background-color: #0B5394 !important;
        }
        
        
    </style>
""", unsafe_allow_html=True)

# Check authentication (can be enhanced based on your needs)
if not os.getenv('INSTAGRAM_PAGE_ACCESS_TOKEN'):
    st.error("Please log in first")
    st.stop()

def auto_refresh():
    """Auto refresh the dashboard every few seconds"""
    count = st.empty()
    for seconds in range(5, 0, -1):
        #count.write(f"Refreshing in {seconds} seconds...")
        sleep(1)
    #count.write("Refreshing...")
    st.rerun()

# Sidebar - User Selection
st.sidebar.title("Instagram Chats")

# Add status filter
status_filter = st.sidebar.radio(
    label="Show conversations",
    options=["Assistant", "Human"],
    key="status_filter",
    horizontal=True,
)

# Get users based on status
users = get_users_by_status(status_filter.lower())

# Create user display options
user_options = []
user_id_map = {}
for user in users:
    user_id = user['sender_id']
    user_info = get_user_info(user_id)
    display_name = f"{user_info['username']}" if user_info and user_info['username'] else f"User {user_id}"
    user_options.append(display_name)
    user_id_map[display_name] = user_id

# Initialize session state for selected user if not exists
if 'selected_user' not in st.session_state:
    st.session_state['selected_user'] = None

# Create the styled selectbox with a proper label
selected_name = st.sidebar.selectbox(
    label="Select conversation",
    options=user_options if user_options else [],
    index=None,
    placeholder="Select a user...",
)

# Update selected user when selection changes
if selected_name:
    st.session_state['selected_user'] = user_id_map[selected_name]

# Main chat area
if st.session_state['selected_user']:
    # Change column ratio to give more space to right pane
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get user info and status
        user_info = get_user_info(st.session_state['selected_user'])
        username = user_info['username'] if user_info and user_info['username'] else st.session_state['selected_user']
        current_status = status_filter.lower()
        
        st.title(f"{username} ({current_status})")
        
        # Chat messages container
        chat_container = st.container()
        with chat_container:
            # Get messages for selected user
            messages = get_user_messages(st.session_state['selected_user'])
            
            # Display messages
            for msg in messages:
                message_class = "message-sent" if msg['is_from_me'] else "message-received"
                with st.container():
                    st.markdown(f"""
                        <div class="chat-message {message_class}">
                            <div>{msg['message']}</div>
                            <div class="timestamp">{msg['timestamp']}</div>
                        </div>
                    """, unsafe_allow_html=True)
    
    with col2:
        # Auto-refresh toggle at the top
        auto_refresh_enabled = st.toggle('Auto Refresh', value=True)
        
        # Message input for human conversations
        if current_status == 'human':
            st.markdown("<h3>Send Message</h3>", unsafe_allow_html=True)
            
            message_input = st.text_area(
                "Type your message",
                key="message_input",
                label_visibility="collapsed",
                height=100
            )
            
            col1_buttons, col2_buttons = st.columns(2)
            
            with col1_buttons:
                if st.button("Send", use_container_width=True):
                    if message_input and message_input.strip():
                        # Initialize Instagram API
                        instagram = InstagramAPI(
                            access_token=os.getenv('INSTAGRAM_PAGE_ACCESS_TOKEN'),
                            ig_user_id=os.getenv('INSTAGRAM_BUSINESS_ID')
                        )
                        
                        # Send message
                        result = instagram.send_message(
                            st.session_state['selected_user'], 
                            message_input.strip()
                        )
                        
                        if result:
                            # Save message to database
                            save_message(
                                st.session_state['selected_user'], 
                                message_input.strip(),
                                is_from_me=True
                            )
                            st.toast("Message sent successfully!")
                            st.session_state.message_input = ""
                        else:
                            st.error("Failed to send message")
            
            with col2_buttons:
                if st.button("Return to Assistant", use_container_width=True):
                    if set_conversation_status(st.session_state['selected_user']):
                        # Send a notification message to user
                        instagram = InstagramAPI(
                            access_token=os.getenv('INSTAGRAM_PAGE_ACCESS_TOKEN'),
                            ig_user_id=os.getenv('INSTAGRAM_BUSINESS_ID')
                        )
                        
                        notification = "You are now being transferred back to our AI assistant."
                        instagram.send_message(st.session_state['selected_user'], notification)
                        save_message(st.session_state['selected_user'], notification, is_from_me=True)
                        
                        st.toast("Conversation returned to Assistant mode")
                        st.rerun()
                    else:
                        st.error("Failed to switch conversation mode")

        # Handle auto-refresh if enabled
        if auto_refresh_enabled:
            auto_refresh()
else:
    st.info("Select a user from the sidebar to view conversation")

# Optional: Manual refresh button
#if st.button("Refresh Now"):
 #   st.rerun()
