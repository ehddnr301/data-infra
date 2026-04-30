-- AI discussion layer: posts, nested comments, idempotent upvotes.
CREATE TABLE IF NOT EXISTS discussion_posts (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
  content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 4000),
  user_email TEXT NOT NULL,
  user_name TEXT,
  source TEXT NOT NULL DEFAULT 'ai-assisted'
    CHECK (source IN ('human', 'ai-auto', 'ai-assisted')),
  dataset_id TEXT,
  listing_id TEXT,
  query_history_id TEXT,
  upvote_count INTEGER NOT NULL DEFAULT 0,
  comment_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (dataset_id) REFERENCES catalog_datasets(id) ON DELETE SET NULL,
  FOREIGN KEY (listing_id) REFERENCES marketplace_listings(id) ON DELETE SET NULL,
  FOREIGN KEY (query_history_id) REFERENCES query_history(id) ON DELETE SET NULL,
  CHECK (dataset_id IS NOT NULL OR listing_id IS NOT NULL OR query_history_id IS NOT NULL)
);

CREATE INDEX idx_discussion_posts_popular
  ON discussion_posts (upvote_count DESC, created_at DESC);
CREATE INDEX idx_discussion_posts_latest
  ON discussion_posts (created_at DESC);
CREATE INDEX idx_discussion_posts_dataset
  ON discussion_posts (dataset_id, upvote_count DESC, created_at DESC);
CREATE INDEX idx_discussion_posts_listing
  ON discussion_posts (listing_id, upvote_count DESC, created_at DESC);
CREATE INDEX idx_discussion_posts_query
  ON discussion_posts (query_history_id, upvote_count DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS discussion_comments (
  id TEXT PRIMARY KEY,
  post_id TEXT NOT NULL,
  parent_comment_id TEXT,
  user_email TEXT NOT NULL,
  user_name TEXT,
  content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 2000),
  source TEXT NOT NULL DEFAULT 'ai-assisted'
    CHECK (source IN ('human', 'ai-auto', 'ai-assisted')),
  upvote_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (post_id) REFERENCES discussion_posts(id) ON DELETE CASCADE,
  FOREIGN KEY (parent_comment_id) REFERENCES discussion_comments(id) ON DELETE CASCADE
);

CREATE INDEX idx_discussion_comments_post
  ON discussion_comments (post_id, created_at ASC, id ASC);
CREATE INDEX idx_discussion_comments_parent
  ON discussion_comments (parent_comment_id, created_at ASC, id ASC);

CREATE TABLE IF NOT EXISTS discussion_votes (
  id TEXT PRIMARY KEY,
  target_type TEXT NOT NULL CHECK (target_type IN ('post', 'comment')),
  target_id TEXT NOT NULL,
  user_email TEXT NOT NULL,
  user_name TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (target_type, target_id, user_email)
);

CREATE INDEX idx_discussion_votes_target
  ON discussion_votes (target_type, target_id);
CREATE INDEX idx_discussion_votes_user
  ON discussion_votes (user_email, created_at DESC);
