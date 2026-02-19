-- 0007_discord_indexes.sql
-- Discord 메시지 인덱스

CREATE INDEX IF NOT EXISTS idx_discord_messages_channel_created
    ON discord_messages(channel_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_discord_messages_author
    ON discord_messages(author_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_discord_messages_batch
    ON discord_messages(batch_date);

CREATE INDEX IF NOT EXISTS idx_discord_messages_reply
    ON discord_messages(referenced_message_id)
    WHERE referenced_message_id IS NOT NULL;
