-- 0008_add_source_column.sql
-- 14개 DL 테이블에 source 컬럼 추가
-- 기존 데이터는 DEFAULT 'gharchive'로 자동 설정
-- REST API 수집 이벤트는 source='rest_api'로 구분

ALTER TABLE dl_push_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_pull_request_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_issues_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_issue_comment_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_watch_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_fork_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_create_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_delete_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_pull_request_review_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_pull_request_review_comment_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_member_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_gollum_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_release_events ADD COLUMN source TEXT DEFAULT 'gharchive';
ALTER TABLE dl_public_events ADD COLUMN source TEXT DEFAULT 'gharchive';
