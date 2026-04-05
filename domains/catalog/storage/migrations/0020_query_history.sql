-- Query history for tracking SQL queries executed through the query dashboard
CREATE TABLE IF NOT EXISTS query_history (
  id TEXT PRIMARY KEY,
  user_email TEXT NOT NULL,
  user_name TEXT,
  executed_sql TEXT NOT NULL,
  row_count INTEGER,
  execution_ms INTEGER,
  status TEXT NOT NULL DEFAULT 'success',
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  ai_explanation TEXT,
  ai_explanation_model TEXT,
  ai_explained_at TEXT
);

CREATE INDEX idx_query_history_user ON query_history(user_email, created_at DESC);
CREATE INDEX idx_query_history_created ON query_history(created_at DESC);
