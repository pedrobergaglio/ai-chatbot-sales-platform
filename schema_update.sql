
-- Update users table to handle multiple platforms
ALTER TABLE users ADD COLUMN platform TEXT DEFAULT 'instagram';
ALTER TABLE users ADD COLUMN phone_number TEXT; -- For WhatsApp users
ALTER TABLE users ADD COLUMN business_name TEXT; -- For business info

-- Expand auth_tokens table to support multiple platforms
ALTER TABLE auth_tokens RENAME TO old_auth_tokens;

CREATE TABLE auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT NOT NULL, -- Generic ID field (can be ig_business_id or waba_id)
    platform TEXT NOT NULL DEFAULT 'instagram', -- 'instagram' or 'whatsapp'
    access_token TEXT NOT NULL,
    token_type TEXT NOT NULL DEFAULT 'user_token',
    phone_number_id TEXT, -- For WhatsApp
    waba_id TEXT, -- WhatsApp Business Account ID
    system_user_id TEXT, -- For WhatsApp System User
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(business_id, platform)
);

-- Migrate existing data
INSERT INTO auth_tokens (business_id, platform, access_token, token_type, expires_at, created_at)
SELECT ig_business_id, 'instagram', access_token, token_type, expires_at, created_at 
FROM old_auth_tokens;

-- Update messages table to better handle multiple platforms
CREATE INDEX IF NOT EXISTS idx_messages_platform ON messages(channel);
