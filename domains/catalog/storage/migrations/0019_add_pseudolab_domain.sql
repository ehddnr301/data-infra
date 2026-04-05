-- Add 'pseudolab' to domain CHECK constraints.
-- D1 does not support ALTER TABLE for CHECK, so we recreate affected tables.

PRAGMA defer_foreign_keys = ON;

-- ============================================================
-- 1) catalog_datasets  (0012 schema + 0015 ALTER ADD 3 columns)
-- ============================================================
CREATE TABLE IF NOT EXISTS catalog_datasets_new (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members', 'pseudolab')),
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  schema_json TEXT CHECK (schema_json IS NULL OR json_valid(schema_json)),
  lineage_json TEXT CHECK (lineage_json IS NULL OR json_valid(lineage_json)),
  owner TEXT,
  tags TEXT CHECK (tags IS NULL OR json_valid(tags)),
  created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
  updated_at TEXT NOT NULL CHECK (updated_at GLOB '????-??-??T??:??:??*'),
  purpose TEXT,
  limitations TEXT,
  usage_examples TEXT
);

INSERT INTO catalog_datasets_new (
  id, domain, name, description, schema_json, lineage_json,
  owner, tags, created_at, updated_at, purpose, limitations, usage_examples
)
SELECT
  id, domain, name, description, schema_json, lineage_json,
  owner, tags, created_at, updated_at, purpose, limitations, usage_examples
FROM catalog_datasets;

DROP TABLE catalog_datasets;
ALTER TABLE catalog_datasets_new RENAME TO catalog_datasets;

CREATE INDEX IF NOT EXISTS idx_catalog_datasets_domain_updated_at
  ON catalog_datasets(domain, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_catalog_datasets_name
  ON catalog_datasets(name);

-- ============================================================
-- 2) glossary_terms  (0009 schema)
-- ============================================================
CREATE TABLE IF NOT EXISTS glossary_terms_new (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members', 'pseudolab')),
  term TEXT NOT NULL,
  definition TEXT NOT NULL,
  related_terms TEXT NOT NULL DEFAULT '[]'
    CHECK (json_valid(related_terms) AND json_type(related_terms) = 'array'),
  created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
  updated_at TEXT NOT NULL CHECK (updated_at GLOB '????-??-??T??:??:??*')
);

INSERT INTO glossary_terms_new (
  id, domain, term, definition, related_terms, created_at, updated_at
)
SELECT
  id, domain, term, definition, related_terms, created_at, updated_at
FROM glossary_terms;

DROP TABLE glossary_terms;
ALTER TABLE glossary_terms_new RENAME TO glossary_terms;

CREATE INDEX IF NOT EXISTS idx_glossary_terms_domain_updated_at
  ON glossary_terms(domain, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_term
  ON glossary_terms(term);

-- ============================================================
-- 3) marketplace_listings  (0017 schema)
-- ============================================================
CREATE TABLE IF NOT EXISTS marketplace_listings_new (
  id TEXT PRIMARY KEY,
  dataset_id TEXT NOT NULL UNIQUE,
  domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members', 'pseudolab')),
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

INSERT INTO marketplace_listings_new (
  id, dataset_id, domain, slug, owner_id, title, subtitle, description,
  category, coverage_summary, update_frequency, documentation_url,
  last_verified_at, created_at, updated_at
)
SELECT
  id, dataset_id, domain, slug, owner_id, title, subtitle, description,
  category, coverage_summary, update_frequency, documentation_url,
  last_verified_at, created_at, updated_at
FROM marketplace_listings;

DROP TABLE marketplace_listings;
ALTER TABLE marketplace_listings_new RENAME TO marketplace_listings;

CREATE INDEX IF NOT EXISTS idx_marketplace_listings_domain_updated
  ON marketplace_listings (domain, updated_at DESC, title ASC);

PRAGMA defer_foreign_keys = OFF;
