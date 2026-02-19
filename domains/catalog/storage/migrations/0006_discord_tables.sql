-- 0006_discord_tables.sql
-- Discord 도메인 테이블: 메시지 원본 + watermark 수집 상태 관리

CREATE TABLE IF NOT EXISTS discord_messages (
    id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_username TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    message_type INTEGER NOT NULL DEFAULT 0,
    referenced_message_id TEXT,
    attachment_count INTEGER NOT NULL DEFAULT 0,
    embed_count INTEGER NOT NULL DEFAULT 0,
    reaction_count INTEGER NOT NULL DEFAULT 0,
    mention_count INTEGER NOT NULL DEFAULT 0,
    pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)),
    created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'),
    edited_at TEXT,
    batch_date TEXT NOT NULL CHECK (batch_date GLOB '????-??-??')
);

CREATE TABLE IF NOT EXISTS discord_watermarks (
    channel_id TEXT PRIMARY KEY,
    channel_name TEXT NOT NULL,
    last_message_id TEXT NOT NULL DEFAULT '0',
    scan_cursor TEXT,
    last_collected_at TEXT NOT NULL CHECK (last_collected_at GLOB '????-??-??T??:??:??*'),
    total_collected INTEGER NOT NULL DEFAULT 0
);
