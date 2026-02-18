-- 0003_dl_event_tables.sql
-- 이벤트 타입별 DL(Data Lineage) 테이블 14개 생성
-- 기존 events 테이블의 단일 payload JSON → 타입별 정규화된 컬럼 구조로 전환

-- 1) dl_push_events — PushEvent (커밋 단위 펼침, 복합 PK)
CREATE TABLE IF NOT EXISTS dl_push_events (
  event_id           TEXT NOT NULL,
  repo_name          TEXT NOT NULL,
  organization       TEXT,
  user_login         TEXT NOT NULL,
  ref_full           TEXT,
  ref_name           TEXT,
  is_branch_ref      INTEGER NOT NULL DEFAULT 0 CHECK (is_branch_ref IN (0,1)),
  is_tag_ref         INTEGER NOT NULL DEFAULT 0 CHECK (is_tag_ref IN (0,1)),
  head_sha           TEXT,
  before_sha         TEXT,
  commit_sha         TEXT NOT NULL,
  commit_author_name  TEXT,
  commit_author_email TEXT,
  commit_message     TEXT,
  commit_distinct    INTEGER CHECK (commit_distinct IS NULL OR commit_distinct IN (0,1)),
  commit_url         TEXT,
  ts_kst             TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date          TEXT NOT NULL CHECK (base_date GLOB '????-??-??'),
  PRIMARY KEY (event_id, commit_sha)
);

-- 2) dl_pull_request_events — PullRequestEvent
CREATE TABLE IF NOT EXISTS dl_pull_request_events (
  event_id              TEXT PRIMARY KEY,
  repo_name             TEXT NOT NULL,
  organization          TEXT,
  user_login            TEXT NOT NULL,
  pr_action             TEXT,
  pr_number             INTEGER,
  pr_title              TEXT,
  pr_html_url           TEXT,
  pr_state              TEXT,
  is_draft              INTEGER CHECK (is_draft IS NULL OR is_draft IN (0,1)),
  pr_body               TEXT,
  pr_author_login       TEXT,
  pr_author_id          INTEGER,
  head_ref              TEXT,
  base_ref              TEXT,
  head_sha              TEXT,
  base_sha              TEXT,
  commits_count         INTEGER,
  additions             INTEGER,
  deletions             INTEGER,
  changed_files         INTEGER,
  issue_comments_count  INTEGER,
  review_comments_count INTEGER,
  is_merged             INTEGER CHECK (is_merged IS NULL OR is_merged IN (0,1)),
  merge_commit_sha      TEXT,
  ts_kst                TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date             TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 3) dl_issues_events — IssuesEvent
CREATE TABLE IF NOT EXISTS dl_issues_events (
  event_id             TEXT PRIMARY KEY,
  repo_name            TEXT NOT NULL,
  organization         TEXT,
  user_login           TEXT NOT NULL,
  issue_action         TEXT,
  issue_number         INTEGER,
  issue_title          TEXT,
  issue_body           TEXT,
  issue_state          TEXT,
  issue_html_url       TEXT,
  issue_author_login   TEXT,
  issue_author_id      INTEGER,
  ts_kst               TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date            TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 4) dl_issue_comment_events — IssueCommentEvent
CREATE TABLE IF NOT EXISTS dl_issue_comment_events (
  event_id             TEXT PRIMARY KEY,
  repo_name            TEXT NOT NULL,
  organization         TEXT,
  user_login           TEXT NOT NULL,
  ic_action            TEXT,
  issue_number         INTEGER,
  issue_title          TEXT,
  issue_state          TEXT,
  issue_html_url       TEXT,
  issue_author_login   TEXT,
  issue_author_id      INTEGER,
  comment_id           INTEGER,
  comment_html_url     TEXT,
  comment_body         TEXT,
  commenter_login      TEXT,
  commenter_id         INTEGER,
  ts_kst               TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date            TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 5) dl_watch_events — WatchEvent
CREATE TABLE IF NOT EXISTS dl_watch_events (
  event_id       TEXT PRIMARY KEY,
  repo_name      TEXT NOT NULL,
  organization   TEXT,
  user_login     TEXT NOT NULL,
  ts_kst         TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date      TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 6) dl_fork_events — ForkEvent
CREATE TABLE IF NOT EXISTS dl_fork_events (
  event_id              TEXT PRIMARY KEY,
  repo_name             TEXT NOT NULL,
  organization          TEXT,
  user_login            TEXT NOT NULL,
  forkee_id             INTEGER,
  forkee_full_name      TEXT,
  forkee_html_url       TEXT,
  forkee_owner_login    TEXT,
  forkee_owner_id       INTEGER,
  forkee_description    TEXT,
  is_fork_private       INTEGER CHECK (is_fork_private IS NULL OR is_fork_private IN (0,1)),
  forkee_default_branch TEXT,
  ts_kst                TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date             TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 7) dl_create_events — CreateEvent
CREATE TABLE IF NOT EXISTS dl_create_events (
  event_id             TEXT PRIMARY KEY,
  repo_name            TEXT NOT NULL,
  organization         TEXT,
  user_login           TEXT NOT NULL,
  created_ref_type     TEXT,
  created_ref_name     TEXT,
  default_branch       TEXT,
  repo_description     TEXT,
  pusher_type          TEXT,
  is_repo_creation     INTEGER NOT NULL DEFAULT 0 CHECK (is_repo_creation IN (0,1)),
  is_branch_creation   INTEGER NOT NULL DEFAULT 0 CHECK (is_branch_creation IN (0,1)),
  is_tag_creation      INTEGER NOT NULL DEFAULT 0 CHECK (is_tag_creation IN (0,1)),
  ts_kst               TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date            TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 8) dl_delete_events — DeleteEvent
CREATE TABLE IF NOT EXISTS dl_delete_events (
  event_id             TEXT PRIMARY KEY,
  repo_name            TEXT NOT NULL,
  organization         TEXT,
  user_login           TEXT NOT NULL,
  deleted_ref_type     TEXT,
  deleted_ref_name     TEXT,
  pusher_type          TEXT,
  is_branch_deletion   INTEGER NOT NULL DEFAULT 0 CHECK (is_branch_deletion IN (0,1)),
  is_tag_deletion      INTEGER NOT NULL DEFAULT 0 CHECK (is_tag_deletion IN (0,1)),
  ts_kst               TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date            TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 9) dl_pull_request_review_events — PullRequestReviewEvent
CREATE TABLE IF NOT EXISTS dl_pull_request_review_events (
  event_id                  TEXT PRIMARY KEY,
  repo_name                 TEXT NOT NULL,
  organization              TEXT,
  user_login                TEXT NOT NULL,
  reviewer_login            TEXT,
  reviewer_id               INTEGER,
  review_state              TEXT,
  review_body               TEXT,
  review_html_url           TEXT,
  commit_sha                TEXT,
  review_submitted_at_utc   TEXT,
  review_submitted_at_kst   TEXT,
  pr_number                 INTEGER,
  pr_title                  TEXT,
  pr_html_url               TEXT,
  pr_author_login           TEXT,
  ts_kst                    TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date                 TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 10) dl_pull_request_review_comment_events — PullRequestReviewCommentEvent
CREATE TABLE IF NOT EXISTS dl_pull_request_review_comment_events (
  event_id                   TEXT PRIMARY KEY,
  repo_name                  TEXT NOT NULL,
  organization               TEXT,
  user_login                 TEXT NOT NULL,
  pr_review_comment_action   TEXT,
  review_comment_id          INTEGER,
  review_comment_html_url    TEXT,
  review_comment_body        TEXT,
  diff_hunk                  TEXT,
  file_path                  TEXT,
  commit_id                  TEXT,
  review_id                  INTEGER,
  commenter_login            TEXT,
  commenter_id               INTEGER,
  pr_number                  INTEGER,
  pr_title                   TEXT,
  pr_html_url                TEXT,
  pr_state                   TEXT,
  ts_kst                     TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date                  TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 11) dl_member_events — MemberEvent
CREATE TABLE IF NOT EXISTS dl_member_events (
  event_id           TEXT PRIMARY KEY,
  repo_name          TEXT NOT NULL,
  organization       TEXT,
  user_login         TEXT NOT NULL,
  member_login       TEXT,
  member_id          INTEGER,
  member_html_url    TEXT,
  member_action      TEXT,
  is_member_added    INTEGER NOT NULL DEFAULT 0 CHECK (is_member_added IN (0,1)),
  is_member_removed  INTEGER NOT NULL DEFAULT 0 CHECK (is_member_removed IN (0,1)),
  ts_kst             TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date          TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 12) dl_gollum_events — GollumEvent (페이지 단위 펼침, 복합 PK)
CREATE TABLE IF NOT EXISTS dl_gollum_events (
  event_id         TEXT NOT NULL,
  repo_name        TEXT NOT NULL,
  organization     TEXT,
  user_login       TEXT NOT NULL,
  page_name        TEXT NOT NULL,
  page_title       TEXT,
  page_summary     TEXT,
  page_action      TEXT,
  page_sha         TEXT,
  page_html_url    TEXT,
  is_page_created  INTEGER NOT NULL DEFAULT 0 CHECK (is_page_created IN (0,1)),
  is_page_edited   INTEGER NOT NULL DEFAULT 0 CHECK (is_page_edited IN (0,1)),
  is_page_deleted  INTEGER NOT NULL DEFAULT 0 CHECK (is_page_deleted IN (0,1)),
  ts_kst           TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date        TEXT NOT NULL CHECK (base_date GLOB '????-??-??'),
  PRIMARY KEY (event_id, page_name)
);

-- 13) dl_release_events — ReleaseEvent
CREATE TABLE IF NOT EXISTS dl_release_events (
  event_id               TEXT PRIMARY KEY,
  repo_name              TEXT NOT NULL,
  organization           TEXT,
  user_login             TEXT NOT NULL,
  release_action         TEXT,
  tag_name               TEXT,
  release_name           TEXT,
  is_prerelease          INTEGER CHECK (is_prerelease IS NULL OR is_prerelease IN (0,1)),
  release_html_url       TEXT,
  release_author_login   TEXT,
  ts_kst                 TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date              TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);

-- 14) dl_public_events — PublicEvent
CREATE TABLE IF NOT EXISTS dl_public_events (
  event_id       TEXT PRIMARY KEY,
  repo_name      TEXT NOT NULL,
  organization   TEXT,
  user_login     TEXT NOT NULL,
  ts_kst         TEXT NOT NULL CHECK (ts_kst GLOB '????-??-??T??:??:??*'),
  base_date      TEXT NOT NULL CHECK (base_date GLOB '????-??-??')
);
