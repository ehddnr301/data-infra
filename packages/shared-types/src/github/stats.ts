import type { IsoDate } from '../common/scalars'

// D1 daily_stats 테이블 Row
export type DailyStatsRow = {
  date: IsoDate
  org_name: string
  repo_name: string
  event_type: string
  count: number
}
