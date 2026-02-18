-- 0004_dl_indexes.sql
-- DL 테이블 인덱스 생성

-- ── 공통 인덱스: 모든 DL 테이블에 base_date + (organization, repo_name) ──

CREATE INDEX IF NOT EXISTS idx_dl_push_events_base_date ON dl_push_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_push_events_org_repo ON dl_push_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_pull_request_events_base_date ON dl_pull_request_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_pull_request_events_org_repo ON dl_pull_request_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_issues_events_base_date ON dl_issues_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_issues_events_org_repo ON dl_issues_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_issue_comment_events_base_date ON dl_issue_comment_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_issue_comment_events_org_repo ON dl_issue_comment_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_watch_events_base_date ON dl_watch_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_watch_events_org_repo ON dl_watch_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_fork_events_base_date ON dl_fork_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_fork_events_org_repo ON dl_fork_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_create_events_base_date ON dl_create_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_create_events_org_repo ON dl_create_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_delete_events_base_date ON dl_delete_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_delete_events_org_repo ON dl_delete_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_pr_review_events_base_date ON dl_pull_request_review_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_pr_review_events_org_repo ON dl_pull_request_review_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_pr_review_comment_events_base_date ON dl_pull_request_review_comment_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_pr_review_comment_events_org_repo ON dl_pull_request_review_comment_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_member_events_base_date ON dl_member_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_member_events_org_repo ON dl_member_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_gollum_events_base_date ON dl_gollum_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_gollum_events_org_repo ON dl_gollum_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_release_events_base_date ON dl_release_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_release_events_org_repo ON dl_release_events(organization, repo_name);

CREATE INDEX IF NOT EXISTS idx_dl_public_events_base_date ON dl_public_events(base_date);
CREATE INDEX IF NOT EXISTS idx_dl_public_events_org_repo ON dl_public_events(organization, repo_name);

-- ── 추가 인덱스: 고빈도 쿼리 패턴 ──

-- PR 분석용
CREATE INDEX IF NOT EXISTS idx_dl_pr_events_repo_action ON dl_pull_request_events(repo_name, pr_action);
CREATE INDEX IF NOT EXISTS idx_dl_pr_events_merged ON dl_pull_request_events(base_date, is_merged) WHERE is_merged = 1;

-- 이슈 분석용
CREATE INDEX IF NOT EXISTS idx_dl_issues_events_repo_action ON dl_issues_events(repo_name, issue_action);

-- 리뷰 분석용
CREATE INDEX IF NOT EXISTS idx_dl_pr_review_events_state ON dl_pull_request_review_events(review_state);
