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

def save_message(sender_id, message, is_from_me=False, human_help_flag=False):
    """Updated save_message function to include human_help_flag"""
    with get_db() as db:
        db.execute(
            'INSERT INTO messages (sender_id, message, is_from_me, human_help_flag) VALUES (?, ?, ?, ?)',
            (sender_id, message, is_from_me, human_help_flag)
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

def save_user_info(sender_id, username=None):
    with get_db() as db:
        db.execute('''
            INSERT OR REPLACE INTO users (sender_id, username) 
            VALUES (?, ?)
        ''', (sender_id, username))
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

def save_auth_token(ig_business_id, access_token, token_type='instagram_user', expires_at=None):
    """Store auth token with proper format and error handling"""
    with get_db() as db:
        try:
            # Clean the business ID to ensure no comments are included
            clean_business_id = str(ig_business_id).strip()
            
            query = '''
                INSERT OR REPLACE INTO auth_tokens 
                (ig_business_id, access_token, token_type, expires_at) 
                VALUES (?, ?, ?, ?)
            '''
            params = (clean_business_id, str(access_token), token_type, expires_at)
            print(f"Executing query: {query} with params: {params}")
            db.execute(query, params)
            db.commit()
            return True
        except Exception as e:
            print(f"Error saving token for {ig_business_id}: {e}")
            db.rollback()
            return False

def get_auth_token(ig_business_id):
    """Get auth token with proper type conversion and debug"""
    with get_db() as db:
        try:
            # Clean the business ID to ensure no comments are included
            clean_business_id = str(ig_business_id).strip()
            
            row = db.execute('''
                SELECT * FROM auth_tokens 
                WHERE ig_business_id = ?
            ''', (clean_business_id,)).fetchone()
            
            return dict_from_row(row) if row else None
        except Exception as e:
            print(f"Error retrieving token for {ig_business_id}: {e}")
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
            SELECT DISTINCT m.sender_id, u.username, cs.status, cs.last_updated
            FROM messages m
            LEFT JOIN users u ON m.sender_id = u.sender_id
            LEFT JOIN conversation_status cs ON m.sender_id = cs.sender_id
            WHERE cs.status = ?
            ORDER BY cs.last_updated DESC
        ''', (status,)).fetchall()
