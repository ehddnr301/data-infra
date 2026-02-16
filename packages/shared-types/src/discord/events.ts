import type { IsoDate, IsoDateTime, JsonText } from '../common/scalars'

export type DiscordEventType =
  | 'member_join'
  | 'member_leave'
  | 'voice_join'
  | 'voice_leave'
  | 'reaction_add'
  | 'reaction_remove'
  | 'thread_create'
  | 'thread_delete'

// D1 discord_events 테이블 Row (event_type은 느슨한 string)
export type DiscordEventRow = {
  id: string
  event_type: string
  user_id: string
  user_name: string
  channel_id: string | null
  metadata: JsonText // JSON string
  created_at: IsoDateTime
  batch_date: IsoDate
}

// 외부 수집 원본 (event_type은 느슨한 string)
export type RawDiscordEvent = {
  id: string
  event_type: string
  user_id: string
  user_name: string
  channel_id: string | null
  metadata: Record<string, unknown>
  created_at: string
}

// ETL 정규화 이후 (event_type이 엄격한 DiscordEventType)
export type NormalizedDiscordEvent = {
  id: string
  event_type: DiscordEventType
  user_id: string
  user_name: string
  channel_id: string | null
  metadata: Record<string, unknown>
  created_at: IsoDateTime
}
