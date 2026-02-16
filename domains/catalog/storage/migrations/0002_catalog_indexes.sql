-- =============================================================================
-- [catalog]005 - D1 카탈로그 스키마: 인덱스
-- 쿼리 패턴 기반 성능 최적화 인덱스
-- =============================================================================

-- events 인덱스
CREATE INDEX IF NOT EXISTS idx_events_batch_date ON events(batch_date);
CREATE INDEX IF NOT EXISTS idx_events_org_repo_created_at ON events(org_name, repo_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_created_at ON events(type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_org_created_at_partial ON events(org_name, created_at DESC) WHERE org_name IS NOT NULL;

-- daily_stats 인덱스
CREATE INDEX IF NOT EXISTS idx_daily_stats_org_repo_date ON daily_stats(org_name, repo_name, date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date_event_type ON daily_stats(date DESC, event_type);

-- catalog_datasets 인덱스
CREATE INDEX IF NOT EXISTS idx_catalog_datasets_domain_updated_at ON catalog_datasets(domain, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_catalog_datasets_name ON catalog_datasets(name);

-- catalog_columns 인덱스 (PII 컬럼만 필터링하는 partial index)
CREATE INDEX IF NOT EXISTS idx_catalog_columns_pii_only ON catalog_columns(dataset_id, column_name) WHERE is_pii = 1;
