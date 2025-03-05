CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_from_me BOOLEAN DEFAULT 0,
    channel TEXT DEFAULT 'instagram',
    human_help_flag BOOLEAN DEFAULT 0
);

DROP TABLE IF EXISTS users;
CREATE TABLE users (
    sender_id TEXT PRIMARY KEY,
    username TEXT,
    name TEXT,
    profile_pic TEXT,
    follower_count INTEGER,
    is_user_follow_business BOOLEAN,
    is_business_follow_user BOOLEAN,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS auth_tokens;
CREATE TABLE auth_tokens (
    ig_business_id TEXT NOT NULL,
    access_token TEXT NOT NULL,
    token_type TEXT NOT NULL DEFAULT 'instagram_user',
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ig_business_id)
);

-- Add new table for conversation status
CREATE TABLE IF NOT EXISTS conversation_status (
    sender_id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'assistant' CHECK(status IN ('assistant', 'human')),
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(sender_id)
);

-- Add index for faster status queries
CREATE INDEX IF NOT EXISTS idx_conversation_status ON conversation_status(status);