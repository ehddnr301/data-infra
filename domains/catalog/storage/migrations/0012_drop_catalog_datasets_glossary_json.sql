PRAGMA defer_foreign_keys = on;

CREATE TABLE IF NOT EXISTS catalog_datasets_new (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members')),
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  schema_json TEXT CHECK (schema_json IS NULL OR json_valid(schema_json)),
  lineage_json TEXT CHECK (lineage_json IS NULL OR json_valid(lineage_json)),
  owner TEXT,
  tags TEXT CHECK (tags IS NULL OR json_valid(tags)),
  created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
  updated_at TEXT NOT NULL CHECK (updated_at GLOB '????-??-??T??:??:??*')
);

INSERT INTO catalog_datasets_new (
  id,
  domain,
  name,
  description,
  schema_json,
  lineage_json,
  owner,
  tags,
  created_at,
  updated_at
)
SELECT
  id,
  domain,
  name,
  description,
  schema_json,
  lineage_json,
  owner,
  tags,
  created_at,
  updated_at
FROM catalog_datasets;

DROP TABLE catalog_datasets;
ALTER TABLE catalog_datasets_new RENAME TO catalog_datasets;

CREATE INDEX IF NOT EXISTS idx_catalog_datasets_domain_updated_at ON catalog_datasets(domain, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_catalog_datasets_name ON catalog_datasets(name);

PRAGMA defer_foreign_keys = off;
