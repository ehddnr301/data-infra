import type { IsoDate, IsoDateTime, JsonText } from '../common/scalars'

// gharchive.org 원본 이벤트 타입
export type GitHubEventType =
  | 'PushEvent'
  | 'PullRequestEvent'
  | 'IssuesEvent'
  | 'WatchEvent'
  | 'ForkEvent'
  | 'CreateEvent'
  | 'DeleteEvent'
  | 'IssueCommentEvent'
  | 'PullRequestReviewEvent'
  | 'PullRequestReviewCommentEvent'
  | 'ReleaseEvent'
  | 'CommitCommentEvent'
  | 'MemberEvent'
  | 'PublicEvent'
  | 'GollumEvent'

export type RawGitHubActor = {
  id: number
  login: string
  display_login?: string
  gravatar_id: string
  url: string
  avatar_url: string
}

export type RawGitHubRepo = {
  id: number
  name: string // "org/repo" 형식
  url: string
}

export type RawGitHubOrg = {
  id: number
  login: string
  gravatar_id: string
  url: string
  avatar_url: string
}

// gharchive.org 원본 이벤트 구조 (Raw — type은 느슨한 string)
export type RawGitHubEvent = {
  id: string
  type: string
  actor: RawGitHubActor
  repo: RawGitHubRepo
  org?: RawGitHubOrg
  payload: Record<string, unknown>
  public: boolean
  created_at: string // ISO 8601
}

// ETL 정규화 이후 이벤트 (type이 엄격한 GitHubEventType)
export type NormalizedGitHubEvent = {
  id: string
  type: GitHubEventType
  actor: RawGitHubActor
  repo: RawGitHubRepo
  org?: RawGitHubOrg
  payload: Record<string, unknown>
  public: boolean
  created_at: IsoDateTime
}

// D1 events 테이블 Row (평탄화)
export type EventRow = {
  id: string
  type: string
  actor_login: string
  repo_name: string
  org_name: string | null
  payload: JsonText // JSON.stringify된 payload
  created_at: IsoDateTime
  batch_date: IsoDate
}
