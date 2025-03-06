import sqlite3
from datetime import datetime

def get_db():
    db = sqlite3.connect('messages.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        with open('schema.sql') as f:
            db.executescript(f.read())

def save_message(sender_id, message, is_from_me=False, human_help_flag=False, channel='instagram', 
                message_type='text'):
    """
    Save message to database with platform support
    
    Args:
        sender_id: User's ID
        message: Message content
        is_from_me: Whether message was sent by our system
        human_help_flag: Whether human assistance was required
        channel: 'instagram' or 'whatsapp'
        message_type: 'text', 'image', 'audio', etc.
    """
    with get_db() as db:
        db.execute(
            '''INSERT INTO messages 
               (sender_id, message, is_from_me, human_help_flag, channel, message_type) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (sender_id, message, is_from_me, human_help_flag, channel, message_type)
        )
        db.commit()

def get_messages():
    with get_db() as db:
        return db.execute(
            'SELECT * FROM messages ORDER BY timestamp DESC LIMIT 100'
        ).fetchall()

def get_messages_since(timestamp=None):
    """Get messages since a specific timestamp"""
    with get_db() as db:
        if timestamp:
            return db.execute(
                'SELECT * FROM messages WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 100',
                (timestamp,)
            ).fetchall()
        return get_messages()

def get_unique_users():
    with get_db() as db:
        return db.execute(
            'SELECT DISTINCT sender_id FROM messages'
        ).fetchall()

def get_user_messages(sender_id):
    with get_db() as db:
        return db.execute(
            'SELECT * FROM messages WHERE sender_id = ? ORDER BY timestamp ASC',
            (sender_id,)
        ).fetchall()

def get_user_messages_since(sender_id, timestamp=None):
    """Get user messages since a specific timestamp"""
    with get_db() as db:
        if timestamp:
            return db.execute(
                'SELECT * FROM messages WHERE sender_id = ? AND timestamp > ? ORDER BY timestamp ASC',
                (sender_id, timestamp)
            ).fetchall()
        return get_user_messages(sender_id)

def save_user_info(sender_id, username=None, name=None, profile_pic=None, follower_count=None, 
                  is_user_follow_business=None, is_business_follow_user=None, platform='instagram', 
                  phone_number=None, business_name=None):
    """
    Save comprehensive user info with platform support
    
    Args:
        sender_id: User ID (required)
        username: Username (optional)
        name: Full name (optional)
        profile_pic: Profile picture URL (optional)
        follower_count: Number of followers (optional)
        is_user_follow_business: Whether user follows business (optional)
        is_business_follow_user: Whether business follows user (optional)
        platform: 'instagram' or 'whatsapp' (default: 'instagram')
        phone_number: Phone number for WhatsApp users (optional)
        business_name: Business name (optional)
    """
    with get_db() as db:
        # Get existing user data if any
        existing = db.execute('SELECT * FROM users WHERE sender_id = ?', (sender_id,)).fetchone()
        
        if existing:
            # Update only the fields that are provided
            fields = []
            params = []
            
            if username is not None:
                fields.append('username = ?')
                params.append(username)
            if name is not None:
                fields.append('name = ?')
                params.append(name)
            if profile_pic is not None:
                fields.append('profile_pic = ?')
                params.append(profile_pic)
            if follower_count is not None:
                fields.append('follower_count = ?')
                params.append(follower_count)
            if is_user_follow_business is not None:
                fields.append('is_user_follow_business = ?')
                params.append(is_user_follow_business)
            if is_business_follow_user is not None:
                fields.append('is_business_follow_user = ?')
                params.append(is_business_follow_user)
            if phone_number is not None:
                fields.append('phone_number = ?')
                params.append(phone_number)
            if business_name is not None:
                fields.append('business_name = ?')
                params.append(business_name)
            
            # Always update platform and last_seen
            fields.append('platform = ?')
            params.append(platform)
            fields.append('last_seen = CURRENT_TIMESTAMP')
            
            # Add sender_id at the end for the WHERE clause
            params.append(sender_id)
            
            if fields:
                query = f"UPDATE users SET {', '.join(fields)} WHERE sender_id = ?"
                db.execute(query, params)
        else:
            # Insert new user
            db.execute('''
                INSERT INTO users 
                (sender_id, username, name, profile_pic, follower_count, is_user_follow_business,
                is_business_follow_user, platform, phone_number, business_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sender_id, username, name, profile_pic, follower_count, is_user_follow_business,
                is_business_follow_user, platform, phone_number, business_name))
        
        db.commit()

def get_user_info(sender_id):
    with get_db() as db:
        return db.execute(
            'SELECT * FROM users WHERE sender_id = ?',
            (sender_id,)
        ).fetchone()

def dict_from_row(row):
    """Convert sqlite3.Row to dict"""
    if not row:
        return None
    return {k: row[k] for k in row.keys()}

def save_auth_token(business_id, access_token, platform='instagram', token_type='user_token', 
                    expires_at=None, phone_number_id=None, waba_id=None, system_user_id=None):
    """
    Store auth token with support for both Instagram and WhatsApp
    
    Args:
        business_id: Business ID (Instagram business ID or WhatsApp WABA ID)
        access_token: OAuth access token
        platform: 'instagram' or 'whatsapp'
        token_type: Type of token (default: 'user_token')
        expires_at: Expiry datetime
        phone_number_id: WhatsApp phone number ID
        waba_id: WhatsApp Business Account ID
        system_user_id: WhatsApp system user ID
    """
    with get_db() as db:
        try:
            # Clean the business ID to ensure no comments are included
            clean_business_id = str(business_id).strip()
            
            db.execute('''
                INSERT OR REPLACE INTO auth_tokens 
                (business_id, platform, access_token, token_type, expires_at, 
                phone_number_id, waba_id, system_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (clean_business_id, platform, str(access_token), token_type, 
                expires_at, phone_number_id, waba_id, system_user_id))
            db.commit()
            return True
        except Exception as e:
            print(f"Error saving token for {business_id}: {e}")
            db.rollback()
            return False

def get_auth_token(business_id, platform='instagram'):
    """Get auth token with platform support"""
    with get_db() as db:
        try:
            # Clean the business ID to ensure no comments are included
            clean_business_id = str(business_id).strip()
            
            row = db.execute('''
                SELECT * FROM auth_tokens 
                WHERE business_id = ? AND platform = ?
            ''', (clean_business_id, platform)).fetchone()
            
            return dict_from_row(row) if row else None
        except Exception as e:
            print(f"Error retrieving token for {business_id}: {e}")
            return None

def set_conversation_status(sender_id, status='assistant'):
    """Set the status of a conversation (assistant/human)"""
    with get_db() as db:
        db.execute('''
            INSERT OR REPLACE INTO conversation_status (sender_id, status, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (sender_id, status))
        db.commit()

def get_conversation_status(sender_id):
    """Get the current status of a conversation"""
    with get_db() as db:
        result = db.execute('''
            SELECT status FROM conversation_status WHERE sender_id = ?
        ''', (sender_id,)).fetchone()
        return result['status'] if result else 'assistant'

def get_users_by_status(status='assistant'):
    """Get all users with a specific conversation status"""
    with get_db() as db:
        return db.execute('''
            SELECT DISTINCT u.sender_id, u.username, u.platform, cs.status, cs.last_updated
            FROM users u
            LEFT JOIN conversation_status cs ON u.sender_id = cs.sender_id
            WHERE cs.status = ?
            ORDER BY cs.last_updated DESC
        ''', (status,)).fetchall()

def get_users_by_status_and_platform(status='assistant', platform=None):
    """Get all users with specific conversation status and optional platform filter"""
    with get_db() as db:
        if platform and platform != 'all':
            return db.execute('''
                SELECT DISTINCT u.sender_id, u.username, u.platform, cs.status, cs.last_updated
                FROM users u
                LEFT JOIN conversation_status cs ON u.sender_id = cs.sender_id
                WHERE cs.status = ? AND u.platform = ?
                ORDER BY cs.last_updated DESC
            ''', (status, platform)).fetchall()
        else:
            return get_users_by_status(status)

def get_stats_by_platform():
    """Get message statistics by platform"""
    with get_db() as db:
        return db.execute('''
            SELECT channel, 
                   COUNT(*) as message_count, 
                   COUNT(DISTINCT sender_id) as user_count
            FROM messages
            GROUP BY channel
        ''').fetchall()
