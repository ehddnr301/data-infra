PRAGMA defer_foreign_keys = ON;

DROP INDEX IF EXISTS idx_listing_resources_listing_order;
DROP INDEX IF EXISTS idx_listing_business_needs_listing_order;
DROP INDEX IF EXISTS idx_listing_datasets_listing_order;
DROP INDEX IF EXISTS idx_marketplace_listings_domain_updated;

DROP TABLE IF EXISTS listing_resources;
DROP TABLE IF EXISTS listing_business_needs;
DROP TABLE IF EXISTS listing_datasets;
DROP TABLE IF EXISTS marketplace_listings;

CREATE TABLE IF NOT EXISTS marketplace_listings (
  id TEXT PRIMARY KEY,
  dataset_id TEXT NOT NULL UNIQUE,
  domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members')),
  slug TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  subtitle TEXT,
  description TEXT NOT NULL,
  category TEXT NOT NULL,
  coverage_summary TEXT,
  update_frequency TEXT,
  documentation_url TEXT,
  last_verified_at TEXT,
  created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
  updated_at TEXT NOT NULL CHECK (updated_at GLOB '????-??-??T??:??:??*'),
  FOREIGN KEY (dataset_id) REFERENCES catalog_datasets(id) ON DELETE CASCADE,
  FOREIGN KEY (owner_id) REFERENCES listing_owners(id) ON DELETE CASCADE,
  UNIQUE (domain, slug)
);

CREATE INDEX IF NOT EXISTS idx_marketplace_listings_domain_updated
  ON marketplace_listings (domain, updated_at DESC, title ASC);

CREATE TABLE IF NOT EXISTS listing_datasets (
  listing_id TEXT NOT NULL,
  dataset_id TEXT NOT NULL,
  display_order INTEGER NOT NULL DEFAULT 0,
  is_featured INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
  object_blurb TEXT,
  quick_start_hint TEXT,
  PRIMARY KEY (listing_id, dataset_id),
  FOREIGN KEY (listing_id) REFERENCES marketplace_listings(id) ON DELETE CASCADE,
  FOREIGN KEY (dataset_id) REFERENCES catalog_datasets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_listing_datasets_listing_order
  ON listing_datasets (listing_id, is_featured DESC, display_order ASC);

CREATE TABLE IF NOT EXISTS listing_business_needs (
  id TEXT PRIMARY KEY,
  listing_id TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  display_order INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (listing_id) REFERENCES marketplace_listings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_listing_business_needs_listing_order
  ON listing_business_needs (listing_id, display_order ASC);

CREATE TABLE IF NOT EXISTS listing_resources (
  id TEXT PRIMARY KEY,
  listing_id TEXT NOT NULL,
  dataset_id TEXT,
  resource_type TEXT NOT NULL CHECK (resource_type IN ('sql', 'api', 'notebook', 'documentation')),
  title TEXT NOT NULL,
  summary TEXT,
  url TEXT,
  content TEXT,
  related_dataset_ids TEXT NOT NULL DEFAULT '[]'
    CHECK (json_valid(related_dataset_ids) AND json_type(related_dataset_ids) = 'array'),
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
  updated_at TEXT NOT NULL CHECK (updated_at GLOB '????-??-??T??:??:??*'),
  CHECK (url IS NOT NULL OR content IS NOT NULL),
  FOREIGN KEY (listing_id) REFERENCES marketplace_listings(id) ON DELETE CASCADE,
  FOREIGN KEY (dataset_id) REFERENCES catalog_datasets(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_listing_resources_listing_order
  ON listing_resources (listing_id, display_order ASC);
