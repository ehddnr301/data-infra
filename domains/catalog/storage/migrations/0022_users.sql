-- Users table for OAuth authentication and role-based access control
CREATE TABLE IF NOT EXISTS users (
  email       TEXT PRIMARY KEY,
  name        TEXT,
  picture     TEXT,
  role        TEXT NOT NULL DEFAULT 'pending' CHECK (role IN ('pending', 'member', 'admin')),
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  approved_at TEXT,
  last_login_at TEXT
);

CREATE INDEX idx_users_role ON users(role);
