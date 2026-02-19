-- Discord 도메인 카탈로그 메타데이터 등록

-- ── catalog_datasets: Discord 데이터셋 2개 ──

INSERT OR REPLACE INTO catalog_datasets
  (id, domain, name, description, schema_json, glossary_json, lineage_json, owner, tags, created_at, updated_at)
VALUES
  ('discord.messages.v1', 'discord', 'Discord Messages',
   'Discord 서버 텍스트 채널 메시지 원본. User Token REST API로 수집하며, snowflake ID 기반 incremental 수집을 지원한다.',
   '{"@context":"https://schema.org","@type":"Dataset","name":"Discord Messages","description":"pseudolab Discord 서버 메시지 아카이브","temporalCoverage":"2024-01-01/..","license":"https://creativecommons.org/licenses/by-nc/4.0/"}',
   '{"snowflake":"Discord 고유 ID 체계. 타임스탬프 내장.","channel":"메시지가 오가는 텍스트/음성 채널.","watermark":"채널별 마지막 수집 지점.","referenced_message":"답글 대상 원본 메시지.","embed":"메시지 내 임베드 콘텐츠.","reaction":"이모지 반응.","thread":"스레드 대화 (현재 미수집).","batch_date":"ETL 배치 수집일."}',
   '{"upstream":["Discord REST API v9"],"process":["Discord REST API → [fetch] → 로컬 JSONL","JSONL → [upload r2] → R2 원본 아카이브","JSONL → [upload d1] → discord_messages"],"downstream":["catalog 스키마 브라우저","Discord 도메인 API"]}',
   'data-platform',
   '["discord","messages","community"]',
   '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'),

  ('discord.watermarks.v1', 'discord', 'Discord Watermarks',
   '채널별 수집 상태를 추적하는 운영 메타데이터 테이블. incremental 수집의 시작점과 중단/재개 지점을 관리한다.',
   '{"@context":"https://schema.org","@type":"Dataset","name":"Discord Watermarks","description":"Discord 채널별 수집 상태 관리","isPartOf":"pseudolab Data Platform"}',
   '{"last_message_id":"수집 완료된 최대 snowflake ID.","scan_cursor":"역방향 스캔 중단 지점.","total_collected":"누적 수집 메시지 총 수."}',
   '{"upstream":["discord-etl fetch"],"process":["watermarks → [read] → 수집 시작점 결정","watermarks → [write] → 수집 완료 후 갱신"],"downstream":["Discord 채널 모니터링 API"]}',
   'data-platform',
   '["discord","operational","watermark"]',
   '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z');


-- ── catalog_columns: discord_messages 컬럼 16개 ──

INSERT OR REPLACE INTO catalog_columns (dataset_id, column_name, data_type, description, is_pii, examples) VALUES
  ('discord.messages.v1', 'id', 'TEXT', '메시지 snowflake ID (PK, 멱등키)', 0,
   '["1100000000000000001"]'),
  ('discord.messages.v1', 'channel_id', 'TEXT', '채널 snowflake ID', 0,
   '["944039671707607060"]'),
  ('discord.messages.v1', 'channel_name', 'TEXT', '채널 표시명 (비정규화)', 0,
   '["공지사항","일반"]'),
  ('discord.messages.v1', 'author_id', 'TEXT', '작성자 snowflake ID', 0,
   '["200000000000000001"]'),
  ('discord.messages.v1', 'author_username', 'TEXT', '작성자 Discord 사용자명', 1,
   '["admin_user"]'),
  ('discord.messages.v1', 'content', 'TEXT', '메시지 본문 전체', 1,
   '["안녕하세요!"]'),
  ('discord.messages.v1', 'message_type', 'INTEGER', '메시지 타입 (0=default, 19=reply, 6=pin)', 0,
   '[0, 19, 6]'),
  ('discord.messages.v1', 'referenced_message_id', 'TEXT', '답글 대상 message ID (nullable)', 0,
   '["1100000000000000001"]'),
  ('discord.messages.v1', 'attachment_count', 'INTEGER', '첨부파일 수', 0,
   '[0, 1, 3]'),
  ('discord.messages.v1', 'embed_count', 'INTEGER', '임베드 콘텐츠 수', 0,
   '[0, 1]'),
  ('discord.messages.v1', 'reaction_count', 'INTEGER', '리액션(이모지) 수', 0,
   '[0, 5]'),
  ('discord.messages.v1', 'mention_count', 'INTEGER', '멘션(@) 수', 0,
   '[0, 2]'),
  ('discord.messages.v1', 'pinned', 'INTEGER', '고정 메시지 여부 (0/1)', 0,
   '[0, 1]'),
  ('discord.messages.v1', 'created_at', 'TEXT', '메시지 생성 시각 (ISO 8601 UTC)', 0,
   '["2024-06-15T10:00:00Z"]'),
  ('discord.messages.v1', 'edited_at', 'TEXT', '메시지 수정 시각 (nullable)', 0,
   '["2024-06-15T10:05:00Z"]'),
  ('discord.messages.v1', 'batch_date', 'TEXT', 'ETL 배치 수집일 (YYYY-MM-DD)', 0,
   '["2024-06-15"]');


-- ── catalog_columns: discord_watermarks 컬럼 6개 ──

INSERT OR REPLACE INTO catalog_columns (dataset_id, column_name, data_type, description, is_pii, examples) VALUES
  ('discord.watermarks.v1', 'channel_id', 'TEXT', '채널 snowflake ID (PK)', 0,
   '["944039671707607060"]'),
  ('discord.watermarks.v1', 'channel_name', 'TEXT', '채널 표시명', 0,
   '["공지사항"]'),
  ('discord.watermarks.v1', 'last_message_id', 'TEXT', '수집 완료된 최대 snowflake ID', 0,
   '["1100000000000000005"]'),
  ('discord.watermarks.v1', 'scan_cursor', 'TEXT', '역방향 스캔 중단 지점 (nullable)', 0,
   NULL),
  ('discord.watermarks.v1', 'last_collected_at', 'TEXT', '마지막 수집 시각 (ISO 8601)', 0,
   '["2024-06-15T13:00:00Z"]'),
  ('discord.watermarks.v1', 'total_collected', 'INTEGER', '누적 수집 메시지 수', 0,
   '[150, 3200]');
