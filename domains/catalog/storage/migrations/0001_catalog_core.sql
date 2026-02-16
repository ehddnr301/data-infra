-- =============================================================================
-- [catalog]005 - D1 카탈로그 스키마: 코어 테이블
-- Phase 1 핵심 4개 테이블 (events, daily_stats, catalog_datasets, catalog_columns)
-- =============================================================================

-- 이벤트 원본 테이블
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  actor_login TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  org_name TEXT,
  payload TEXT NOT NULL CHECK (json_valid(payload)),
  created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
  batch_date TEXT NOT NULL CHECK (batch_date GLOB '????-??-??')
);

-- 일별 집계 테이블
CREATE TABLE IF NOT EXISTS daily_stats (
  date TEXT NOT NULL CHECK (date GLOB '????-??-??'),
  org_name TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  event_type TEXT NOT NULL,
  count INTEGER NOT NULL CHECK (count >= 0),
  PRIMARY KEY (date, org_name, repo_name, event_type)
);

-- 카탈로그 데이터셋 메타데이터
CREATE TABLE IF NOT EXISTS catalog_datasets (
  id TEXT PRIMARY KEY,
  domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members')),
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  schema_json TEXT CHECK (schema_json IS NULL OR json_valid(schema_json)),
  glossary_json TEXT CHECK (glossary_json IS NULL OR json_valid(glossary_json)),
  lineage_json TEXT CHECK (lineage_json IS NULL OR json_valid(lineage_json)),
  owner TEXT,
  tags TEXT CHECK (tags IS NULL OR json_valid(tags)),
  created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
  updated_at TEXT NOT NULL CHECK (updated_at GLOB '????-??-??T??:??:??*')
);

-- 카탈로그 컬럼 메타데이터
CREATE TABLE IF NOT EXISTS catalog_columns (
  dataset_id TEXT NOT NULL,
  column_name TEXT NOT NULL,
  data_type TEXT NOT NULL,
  description TEXT,
  is_pii INTEGER NOT NULL DEFAULT 0 CHECK (is_pii IN (0, 1)),
  examples TEXT CHECK (examples IS NULL OR json_valid(examples)),
  PRIMARY KEY (dataset_id, column_name),
  FOREIGN KEY (dataset_id) REFERENCES catalog_datasets(id) ON DELETE CASCADE
);
