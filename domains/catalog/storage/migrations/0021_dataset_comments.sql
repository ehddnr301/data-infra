-- Dataset comments with category and AI source tracking
CREATE TABLE IF NOT EXISTS dataset_comments (
  id TEXT PRIMARY KEY,
  dataset_id TEXT NOT NULL,
  user_email TEXT NOT NULL,
  user_name TEXT,
  category TEXT NOT NULL CHECK (category IN ('limitation', 'purpose', 'usage')),
  content TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'human' CHECK (source IN ('human', 'ai-auto', 'ai-assisted')),
  source_query_ids TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT,
  FOREIGN KEY (dataset_id) REFERENCES catalog_datasets(id) ON DELETE CASCADE
);

CREATE INDEX idx_comments_dataset ON dataset_comments(dataset_id, category, created_at DESC);
CREATE INDEX idx_comments_user ON dataset_comments(user_email, created_at DESC);
CREATE INDEX idx_comments_source ON dataset_comments(source);
