import type { IsoDate } from '../common/scalars'

// D1 discord_daily_stats 테이블 Row
export type DiscordDailyStatsRow = {
  date: IsoDate
  channel_id: string
  channel_name: string
  message_count: number
  unique_authors: number
  reaction_count: number
}
