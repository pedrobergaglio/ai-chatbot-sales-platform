# AI Chatbot Sales Platform for Instagram

An intelligent sales assistant platform that integrates with Instagram's Business API to handle customer inquiries for Soluciones Sauco's construction materials business.

## System Architecture

- **Main Application**: Flask-based backend handling Instagram webhooks and chat interactions
- **Dashboard**: Streamlit-powered real-time chat monitoring interface
- **Nginx**: Reverse proxy managing both the main app and dashboard
- **Database**: SQLite for message and user data storage
- **AI**: OpenAI GPT-4 for intelligent responses

## Key Features

- Instagram Business API integration
- Real-time message handling
- Web-based chat monitoring dashboard
- Context-aware AI responses
- Secure authentication flow
- Message history tracking

## Prerequisites

- Python 3.8+
- Nginx
- Instagram Business Account
- OpenAI API access

## Environment Variables

```env
OPENAI_API_KEY=your_openai_key
INSTAGRAM_CLIENT_ID=your_instagram_app_id
INSTAGRAM_CLIENT_SECRET=your_instagram_app_secret
INSTAGRAM_REDIRECT_URI=your_redirect_uri
VERIFY_TOKEN=your_webhook_verify_token
INSTAGRAM_PAGE_ACCESS_TOKEN=your_page_access_token
FLASK_SECRET_KEY=your_secret_key
```

## Quick Start

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Nginx:
```bash
# The run.py script will handle Nginx setup automatically
python run.py
```

4. Access the platform:
- Main application: http://localhost:7777
- Dashboard: http://localhost:8501/dashboard

## Development Setup

The platform uses a dev tunnel configuration for Instagram webhooks:

```nginx
server {
    listen 80;
    server_name b4fvhl4w-7777.brs.devtunnels.ms;

    # Main application proxy
    location / {
        proxy_pass http://127.0.0.1:7777;
    }

    # Dashboard proxy
    location /dashboard/ {
        return 301 https://b4fvhl4w-8501.brs.devtunnels.ms/dashboard/;
    }
}
```

## Security

- OAuth 2.0 authentication flow with Instagram
- Long-lived access tokens with auto-refresh
- Secure webhook verification
- Session-based user authentication

## Components

1. **Thread Manager** (`thread_manager.py`)
   - Handles AI conversation context
   - Manages message history

2. **Message Handler** (`message_handler.py`)
   - Processes incoming Instagram messages
   - Coordinates AI responses

3. **Instagram API** (`instagram_api.py`)
   - Manages Instagram Graph API interactions
   - Handles message sending and user info retrieval

4. **Dashboard** (`dashboard.py`)
   - Real-time chat monitoring
   - User interaction history
   - Auto-refresh functionality

## License

MIT License