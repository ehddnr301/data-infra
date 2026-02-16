import type { IsoDate, IsoDateTime } from '../common/scalars'

// D1 discord_messages 테이블 Row
export type DiscordMessageRow = {
  id: string // Discord message ID (snowflake)
  channel_id: string
  channel_name: string
  author_id: string
  author_name: string
  content?: string // 수집 정책에 따라 optional
  message_type: string // 'DEFAULT', 'REPLY', 'THREAD_STARTER' 등
  created_at: IsoDateTime
  batch_date: IsoDate
  reaction_count: number
  reply_count: number
}
