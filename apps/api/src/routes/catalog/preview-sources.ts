export const PREVIEW_SOURCE_BY_DATASET_ID: Record<string, { table: string; sortCol: string }> = {
  'github.push-events.v1': { table: 'dl_push_events', sortCol: 'ts_kst' },
  'github.pull-request-events.v1': { table: 'dl_pull_request_events', sortCol: 'ts_kst' },
  'github.issues-events.v1': { table: 'dl_issues_events', sortCol: 'ts_kst' },
  'github.issue-comment-events.v1': { table: 'dl_issue_comment_events', sortCol: 'ts_kst' },
  'github.watch-events.v1': { table: 'dl_watch_events', sortCol: 'ts_kst' },
  'github.fork-events.v1': { table: 'dl_fork_events', sortCol: 'ts_kst' },
  'github.create-events.v1': { table: 'dl_create_events', sortCol: 'ts_kst' },
  'github.delete-events.v1': { table: 'dl_delete_events', sortCol: 'ts_kst' },
  'github.pull-request-review-events.v1': {
    table: 'dl_pull_request_review_events',
    sortCol: 'ts_kst',
  },
  'github.pull-request-review-comment-events.v1': {
    table: 'dl_pull_request_review_comment_events',
    sortCol: 'ts_kst',
  },
  'github.member-events.v1': { table: 'dl_member_events', sortCol: 'ts_kst' },
  'github.gollum-events.v1': { table: 'dl_gollum_events', sortCol: 'ts_kst' },
  'github.release-events.v1': { table: 'dl_release_events', sortCol: 'ts_kst' },
  'github.public-events.v1': { table: 'dl_public_events', sortCol: 'ts_kst' },
  'discord.messages.v1': {
    table: 'discord_messages',
    sortCol: 'created_at',
  },
}

export function hasPreviewSource(datasetId: string): boolean {
  return Object.prototype.hasOwnProperty.call(PREVIEW_SOURCE_BY_DATASET_ID, datasetId)
}
