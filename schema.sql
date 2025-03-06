-- Drop existing tables
-- DROP TABLE IF EXISTS conversation_status;
-- DROP TABLE IF EXISTS messages;
-- DROP TABLE IF EXISTS users;
-- DROP TABLE IF EXISTS auth_tokens;

-- Messages table with platform support
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_from_me BOOLEAN DEFAULT 0,
    channel TEXT DEFAULT 'instagram', -- 'instagram' or 'whatsapp'
    human_help_flag BOOLEAN DEFAULT 0,
    message_type TEXT DEFAULT 'text'  -- 'text', 'image', 'audio', etc.
);

-- Users table with platform support
CREATE TABLE IF NOT EXISTS users (
    sender_id TEXT PRIMARY KEY,
    username TEXT,
    name TEXT, 
    profile_pic TEXT,
    follower_count INTEGER,
    is_user_follow_business BOOLEAN,
    is_business_follow_user BOOLEAN,
    platform TEXT DEFAULT 'instagram', -- 'instagram' or 'whatsapp'
    phone_number TEXT,                -- For WhatsApp users
    business_name TEXT,               -- For business info
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Auth tokens table for both platforms
CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL,        -- Generic ID field (can be ig_business_id or waba_id)
    platform TEXT NOT NULL DEFAULT 'instagram', -- 'instagram' or 'whatsapp'
    access_token TEXT NOT NULL,
    token_type TEXT NOT NULL DEFAULT 'user_token',
    phone_number_id TEXT,             -- For WhatsApp
    waba_id TEXT,                     -- WhatsApp Business Account ID
    system_user_id TEXT,              -- For WhatsApp System User
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(business_id, platform)
);

-- Conversation status table
CREATE TABLE IF NOT EXISTS conversation_status (
    sender_id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'assistant' CHECK(status IN ('assistant', 'human')),
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(sender_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversation_status ON conversation_status(status);
CREATE INDEX IF NOT EXISTS idx_messages_platform ON messages(channel);
CREATE INDEX IF NOT EXISTS idx_users_platform ON users(platform);