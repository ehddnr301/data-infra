-- Personal API Tokens for bot/script authentication
CREATE TABLE IF NOT EXISTS user_api_tokens (
  id TEXT PRIMARY KEY,
  user_email TEXT NOT NULL,
  name TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  token_prefix TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_used_at TEXT,
  FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE
);

CREATE INDEX idx_user_api_tokens_email ON user_api_tokens(user_email);
CREATE INDEX idx_user_api_tokens_hash ON user_api_tokens(token_hash);
