-- Feature Limits Table Migration for SQLite
-- Run with: sqlite3 backend/data/app.db < backend/migrations/033_add_feature_limits_table.sql

-- Create feature_limits table
CREATE TABLE IF NOT EXISTS feature_limits (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL UNIQUE CHECK (role IN ('user', 'premium', 'admin', 'owner')),
    ai_limit REAL NULL,
    storage_limit_bytes INTEGER NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feature_limits_role ON feature_limits(role);

-- Insert default limits
INSERT OR IGNORE INTO feature_limits (id, role, ai_limit, storage_limit_bytes, description)
VALUES
    (lower(hex(randomblob(16))), 'user', 0.00, 20971520, 'Regular user: no AI access without own token, 20MB storage'),
    (lower(hex(randomblob(16))), 'premium', 5.00, 52428800, 'Premium user: $5 AI limit, 50MB storage'),
    (lower(hex(randomblob(16))), 'admin', NULL, 209715200, 'Admin: unlimited AI, 200MB storage'),
    (lower(hex(randomblob(16))), 'owner', NULL, 1073741824, 'Owner: unlimited AI, 1GB storage');

