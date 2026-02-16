-- =============================================================================
-- [catalog]005 - 시드 데이터 (테스트용 샘플)
-- pseudolab 조직 기준 GitHub Archive 이벤트 구조 반영
-- =============================================================================

-- events 시드
INSERT OR IGNORE INTO events (id, type, actor_login, repo_name, org_name, payload, created_at, batch_date) VALUES
('12345678901', 'PushEvent', 'testuser', 'pseudolab/test-repo', 'pseudolab', '{"push_id":999,"size":1}', '2024-01-15T10:30:00Z', '2024-01-15'),
('12345678902', 'IssuesEvent', 'alice', 'pseudolab/test-repo', 'pseudolab', '{"action":"opened","issue":{"number":42}}', '2024-01-15T11:00:00Z', '2024-01-15'),
('12345678903', 'PullRequestEvent', 'bob', 'pseudolab/data-platform', 'pseudolab', '{"action":"opened","number":7}', '2024-01-16T09:00:00Z', '2024-01-16');

-- daily_stats 시드
INSERT OR IGNORE INTO daily_stats (date, org_name, repo_name, event_type, count) VALUES
('2024-01-15', 'pseudolab', 'pseudolab/test-repo', 'PushEvent', 1),
('2024-01-15', 'pseudolab', 'pseudolab/test-repo', 'IssuesEvent', 1),
('2024-01-16', 'pseudolab', 'pseudolab/data-platform', 'PullRequestEvent', 1);

-- catalog_datasets 시드
INSERT OR IGNORE INTO catalog_datasets (id, domain, name, description, schema_json, glossary_json, lineage_json, owner, tags, created_at, updated_at) VALUES
('github.events.v1', 'github', 'GitHub Events', 'GitHub Archive 정규화 이벤트 테이블', '{"@context":"https://schema.org","@type":"Dataset"}', NULL, '{"upstream":["gharchive.org"]}', 'data-platform', '["github","events"]', '2024-01-15T12:00:00Z', '2024-01-15T12:00:00Z'),
('github.daily_stats.v1', 'github', 'GitHub Daily Stats', '일별 GitHub 이벤트 집계 테이블', '{"@context":"https://schema.org","@type":"Dataset"}', NULL, '{"upstream":["github.events.v1"]}', 'data-platform', '["github","stats","aggregation"]', '2024-01-15T12:00:00Z', '2024-01-15T12:00:00Z');

-- catalog_columns 시드 (events 테이블 메타데이터)
INSERT OR IGNORE INTO catalog_columns (dataset_id, column_name, data_type, description, is_pii, examples) VALUES
('github.events.v1', 'id', 'TEXT', '이벤트 고유 ID (멱등성 키)', 0, '["12345678901"]'),
('github.events.v1', 'type', 'TEXT', 'GitHub 이벤트 타입', 0, '["PushEvent","IssuesEvent"]'),
('github.events.v1', 'actor_login', 'TEXT', 'GitHub 사용자 로그인 ID', 0, '["testuser","alice"]'),
('github.events.v1', 'repo_name', 'TEXT', '리포지토리 전체 이름 (org/repo)', 0, '["pseudolab/test-repo"]'),
('github.events.v1', 'org_name', 'TEXT', '조직 이름 (없을 수 있음)', 0, '["pseudolab"]'),
('github.events.v1', 'payload', 'TEXT', '이벤트 페이로드 (JSON)', 0, NULL),
('github.events.v1', 'created_at', 'TEXT', '이벤트 발생 시각 (ISO 8601)', 0, '["2024-01-15T10:30:00Z"]'),
('github.events.v1', 'batch_date', 'TEXT', '배치 처리일 (YYYY-MM-DD)', 0, '["2024-01-15"]');
