-- 0005_drop_events_table.sql
-- 기존 events 테이블 및 관련 인덱스 제거
-- 주의: DL 테이블 이관 및 검증 완료 후에만 적용할 것

-- 기존 events 인덱스 제거
DROP INDEX IF EXISTS idx_events_batch_date;
DROP INDEX IF EXISTS idx_events_org_repo_created_at;
DROP INDEX IF EXISTS idx_events_type_created_at;
DROP INDEX IF EXISTS idx_events_org_created_at_partial;

-- events 테이블 제거
DROP TABLE IF EXISTS events;
