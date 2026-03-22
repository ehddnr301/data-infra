INSERT INTO listing_owners
  (id, slug, display_name, team_name, role_title, bio, avatar_url, contact_email, slack_channel, created_at, updated_at)
VALUES
  ('owner-github', 'github-data', 'GitHub Data Team', 'Data Platform', 'Domain owner',
   'GitHub marketplace datasets를 운영하는 내부 owner.', NULL,
   'github-data@pseudolab.org', '#github-data', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'),
  ('owner-discord', 'discord-data', 'Discord Data Team', 'Data Platform', 'Domain owner',
   'Discord marketplace datasets를 운영하는 내부 owner.', NULL,
   'discord-data@pseudolab.org', '#discord-data', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'),
  ('owner-linkedin', 'linkedin-data', 'LinkedIn Data Team', 'Data Platform', 'Domain owner',
   'LinkedIn marketplace datasets를 위한 placeholder owner.', NULL,
   'linkedin-data@pseudolab.org', '#linkedin-data', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'),
  ('owner-members', 'members-data', 'Members Data Team', 'Data Platform', 'Domain owner',
   'Members marketplace datasets를 위한 placeholder owner.', NULL,
   'members-data@pseudolab.org', '#members-data', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')
ON CONFLICT(id) DO UPDATE SET
  slug = excluded.slug,
  display_name = excluded.display_name,
  team_name = excluded.team_name,
  role_title = excluded.role_title,
  bio = excluded.bio,
  avatar_url = excluded.avatar_url,
  contact_email = excluded.contact_email,
  slack_channel = excluded.slack_channel,
  created_at = excluded.created_at,
  updated_at = excluded.updated_at;

DELETE FROM listing_resources;
DELETE FROM listing_business_needs;
DELETE FROM listing_datasets;
DELETE FROM marketplace_listings;

-- Fallback listing rows for datasets without curated GitHub/Discord overlay metadata.
INSERT OR REPLACE INTO marketplace_listings
  (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at)
SELECT
  'listing-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')) AS id,
  cd.id AS dataset_id,
  cd.domain,
  CASE
    WHEN cd.id LIKE cd.domain || '.%' THEN substr(cd.id, length(cd.domain) + 2)
    ELSE cd.id
  END AS slug,
  CASE cd.domain
    WHEN 'github' THEN 'owner-github'
    WHEN 'discord' THEN 'owner-discord'
    WHEN 'linkedin' THEN 'owner-linkedin'
    ELSE 'owner-members'
  END AS owner_id,
  cd.name AS title,
  CASE cd.domain
    WHEN 'github' THEN 'GitHub operational dataset'
    WHEN 'discord' THEN 'Discord operational dataset'
    WHEN 'linkedin' THEN 'LinkedIn dataset product'
    ELSE 'Members dataset product'
  END AS subtitle,
  COALESCE(cd.purpose, cd.description) AS description,
  CASE cd.domain
    WHEN 'github' THEN 'engineering'
    WHEN 'discord' THEN 'community'
    WHEN 'linkedin' THEN 'linkedin'
    ELSE 'members'
  END AS category,
  CASE cd.domain
    WHEN 'github' THEN 'gharchive.org and GitHub REST API batches filtered to PseudoLab repositories.'
    WHEN 'discord' THEN 'Discord batch collection metadata aligned to approved community channels.'
    ELSE cd.description
  END AS coverage_summary,
  CASE cd.domain
    WHEN 'github' THEN 'daily'
    WHEN 'discord' THEN 'daily_or_weekly'
    ELSE 'internal'
  END AS update_frequency,
  '/api/catalog/datasets/' || cd.id AS documentation_url,
  cd.updated_at AS last_verified_at,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd
WHERE cd.id NOT IN (
  'discord.messages.v1',
  'discord.watermarks.v1',
  'github.push-events.v1',
  'github.create-events.v1',
  'github.watch-events.v1',
  'ds.github.repo.v1'
);

INSERT OR REPLACE INTO marketplace_listings
  (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at)
SELECT
  'listing-discord-messages',
  cd.id,
  cd.domain,
  'messages.v1',
  'owner-discord',
  'Discord Messages',
  'Privacy-aware community message archive',
  '공지/스터디 채널 중심의 Discord 메시지를 batch-first로 수집해 moderation과 engagement 흐름을 privacy-aware 범위 안에서 검토합니다.',
  'community',
  'Discord Bot/API batch collection → R2 raw JSON + D1 discord_messages. DM은 제외하고 public study/community channel 범위를 우선 수집합니다.',
  'daily_or_weekly',
  '/api/catalog/datasets/' || cd.id,
  cd.updated_at,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd
WHERE cd.id = 'discord.messages.v1';

INSERT OR REPLACE INTO marketplace_listings
  (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at)
SELECT
  'listing-discord-watermarks',
  cd.id,
  cd.domain,
  'watermarks.v1',
  'owner-discord',
  'Discord Collector Watermarks',
  'Collector freshness and recovery ledger',
  '채널별 watermark와 scan cursor를 기준으로 Discord 배치 수집 상태를 모니터링하고 recovery/freshness 이슈를 추적합니다.',
  'operations',
  'Discord batch collector watermark table로 채널별 last_message_id, scan_cursor, freshness 상태를 관리합니다.',
  'daily_or_weekly',
  '/api/catalog/datasets/' || cd.id,
  cd.updated_at,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd
WHERE cd.id = 'discord.watermarks.v1';

INSERT OR REPLACE INTO marketplace_listings
  (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at)
SELECT
  'listing-github-push-events',
  cd.id,
  cd.domain,
  'push-events.v1',
  'owner-github',
  cd.name,
  'Daily engineering activity feed',
  'PseudoLab GitHub org와 산하 프로젝트의 push 활동을 일 단위로 정리해 릴리스 cadence와 maintainer throughput을 추적합니다.',
  'engineering',
  'gharchive.org + GitHub REST API daily batches → org/repo filter → R2 raw + D1 dl_push_events/daily_stats.',
  'daily',
  '/api/catalog/datasets/' || cd.id,
  cd.updated_at,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd
WHERE cd.id = 'github.push-events.v1';

INSERT OR REPLACE INTO marketplace_listings
  (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at)
SELECT
  'listing-github-create-events',
  cd.id,
  cd.domain,
  'create-events.v1',
  'owner-github',
  'GitHub Project Builders',
  'Builder and project-start signal',
  '조직 repository creation 이벤트를 기준으로 누가 새 스터디/프로젝트 저장소를 시작했는지 builder 신호를 읽어냅니다.',
  'builders',
  'D1 dl_create_events에서 organization repository creation 행만 builder 신호로 해석하며 branch/tag create는 제외합니다.',
  'daily',
  '/api/catalog/datasets/' || cd.id,
  cd.updated_at,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd
WHERE cd.id = 'github.create-events.v1';

INSERT OR REPLACE INTO marketplace_listings
  (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at)
SELECT
  'listing-github-watch-events',
  cd.id,
  cd.domain,
  'watch-events.v1',
  'owner-github',
  cd.name,
  'Support and interest signal',
  'Watch/star 이벤트를 기반으로 어떤 스터디/프로젝트가 관심과 응원을 받는지 파악하는 support 신호입니다.',
  'community',
  'D1 dl_watch_events 기반 관심 신호이며 내부는 repo membership 또는 prior code contribution evidence로 분리합니다.',
  'daily',
  '/api/catalog/datasets/' || cd.id,
  cd.updated_at,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd
WHERE cd.id = 'github.watch-events.v1';

INSERT OR REPLACE INTO marketplace_listings
  (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at)
SELECT
  'listing-github-repo',
  cd.id,
  cd.domain,
  cd.id,
  'owner-github',
  'GitHub Repository Inventory',
  'Repository inventory and portfolio map',
  'PseudoLab 메인 org와 산하 프로젝트 저장소를 inventory 관점에서 정리해 프로젝트 포트폴리오와 ownership을 파악합니다.',
  'inventory',
  'Repository inventory snapshots로 study/research 포트폴리오, ownership, 운영 범위를 파악합니다.',
  'periodic',
  '/api/catalog/datasets/' || cd.id,
  cd.updated_at,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd
WHERE cd.id = 'ds.github.repo.v1';

-- Fallback business needs for non-curated datasets.
INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT
  'need-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')),
  'listing-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')),
  CASE cd.domain
    WHEN 'github' THEN 'GitHub operations review'
    WHEN 'discord' THEN 'Discord operations review'
    WHEN 'linkedin' THEN 'LinkedIn profile review'
    ELSE 'Member health review'
  END,
  CASE cd.domain
    WHEN 'github' THEN 'GitHub 운영 신호를 점검합니다.'
    WHEN 'discord' THEN 'Discord 운영 신호를 점검합니다.'
    WHEN 'linkedin' THEN 'LinkedIn-facing datasets를 위한 future workflow placeholder입니다.'
    ELSE 'Member-facing datasets를 위한 future workflow placeholder입니다.'
  END,
  1
FROM catalog_datasets cd
WHERE cd.id NOT IN (
  'discord.messages.v1',
  'discord.watermarks.v1',
  'github.push-events.v1',
  'github.create-events.v1',
  'github.watch-events.v1',
  'ds.github.repo.v1'
);

INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT 'need-discord-messages-1', 'listing-discord-messages', 'Moderation and engagement review',
       '공지와 스터디 채널 메시지의 흐름을 privacy-aware 범위에서 함께 검토합니다.', 1
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-discord-messages');

INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT 'need-discord-messages-2', 'listing-discord-messages', 'Privacy-aware collection policy',
       'DM 제외와 public study channel 우선 원칙을 함께 설명합니다.', 2
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-discord-messages');

INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT 'need-discord-watermarks-1', 'listing-discord-watermarks', 'Collector freshness review',
       '수집이 지연되거나 멈춘 채널의 watermark를 복구합니다.', 1
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-discord-watermarks');

INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT 'need-github-push-1', 'listing-github-push-events', 'Release cadence monitoring',
       '스터디/프로젝트 저장소의 코드 흐름과 maintainer activity를 함께 점검합니다.', 1
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-push-events');

INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT 'need-github-create-1', 'listing-github-create-events', 'Community builder detection',
       '새 스터디/프로젝트 저장소가 언제, 누가 시작했는지 builder 신호로 확인합니다.', 1
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-create-events');

INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT 'need-github-watch-1', 'listing-github-watch-events', 'Support signal review',
       '프로젝트별 관심/응원을 내부와 외부로 나눠서 해석합니다.', 1
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-watch-events');

INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT 'need-github-repo-1', 'listing-github-repo', 'Portfolio inventory audit',
       '현재 운영 중인 프로젝트 저장소 포트폴리오와 ownership 현황을 검토합니다.', 1
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-repo');

-- Generic API resource for datasets without curated resource overlays.
INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT
  'resource-detail-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')),
  'listing-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')),
  cd.id,
  'api',
  'Catalog dataset API',
  '내부 catalog truth를 직접 확인합니다.',
  '/api/catalog/datasets/' || cd.id,
  NULL,
  json_array(cd.id),
  1,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd
WHERE cd.id NOT IN (
  'discord.messages.v1',
  'discord.watermarks.v1',
  'github.push-events.v1',
  'github.create-events.v1',
  'github.watch-events.v1',
  'ds.github.repo.v1'
);

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-discord-messages-preview', 'listing-discord-messages', 'discord.messages.v1', 'api',
       'Preview API', '최근 community message preview를 바로 확인합니다.',
       '/api/catalog/datasets/discord.messages.v1/preview', NULL, '[]', 1,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-discord-messages');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-discord-messages-sql', 'listing-discord-messages', 'discord.messages.v1', 'sql',
       'Recent channel activity SQL', '최근 community activity를 SQL로 살펴봅니다.',
       NULL,
       'SELECT channel_name, author_username, created_at FROM discord_messages ORDER BY created_at DESC LIMIT 20;',
       '["discord.messages.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-discord-messages');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-discord-watermarks-api', 'listing-discord-watermarks', 'discord.watermarks.v1', 'api',
       'Dataset API', 'Collector watermark metadata와 최신 검증 시점을 확인합니다.',
       '/api/catalog/datasets/discord.watermarks.v1', NULL, '["discord.watermarks.v1"]', 1,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-discord-watermarks');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-discord-watermarks-sql', 'listing-discord-watermarks', 'discord.watermarks.v1', 'sql',
       'Collector lag SQL', '채널별 수집 지연과 freshness 상태를 점검합니다.',
       NULL,
       'SELECT channel_name, last_message_id, scan_cursor, last_collected_at FROM discord_watermarks ORDER BY last_collected_at ASC LIMIT 20;',
       '["discord.watermarks.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-discord-watermarks');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-push-api', 'listing-github-push-events', 'github.push-events.v1', 'api',
       'Dataset API', 'Catalog metadata와 최신 검증 시점을 확인합니다.',
       '/api/catalog/datasets/github.push-events.v1', NULL, '["github.push-events.v1"]', 1,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-push-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-push-sql', 'listing-github-push-events', 'github.push-events.v1', 'sql',
       'Release cadence SQL', '프로젝트별 push cadence를 빠르게 확인합니다.',
       NULL,
       'SELECT base_date, repo_name, COUNT(DISTINCT event_id) AS push_events FROM dl_push_events WHERE organization = ''pseudolab'' GROUP BY base_date, repo_name ORDER BY base_date DESC, push_events DESC LIMIT 30;',
       '["github.push-events.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-push-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-push-enrich-guide', 'listing-github-push-events', 'github.push-events.v1', 'documentation',
       'Commit enrich lookup guide', 'D1 후보 commit에서 enrich detail로 내려가는 방법을 설명합니다.',
       NULL,
       '1. dl_push_events에서 repo_name, commit_sha 후보를 찾습니다.
2. repo_name을 owner/repo로 분리합니다.
3. github-archive-raw/enriched/commits/{owner}/{repo}/{commit_sha}.json 경로에서 상세 payload를 조회합니다.
4. changed files, commit message, author context를 함께 읽어 실제 기여 내용을 해석합니다.',
       '["github.push-events.v1"]', 3,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-push-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-push-topic-notebook', 'listing-github-push-events', 'github.push-events.v1', 'notebook',
       'Changed-file topic notebook', '최근 push 후보에서 파일/주제 분포를 분석하는 pseudo-notebook입니다.',
       NULL,
       'Step 1: dl_push_events에서 최근 30일 commit 후보를 추출합니다.
Step 2: 각 commit_sha로 enriched/commits/... json을 읽습니다.
Step 3: filename/path prefix 기준으로 docs, app, infra, experiment 같은 topic bucket을 만듭니다.
Step 4: contributor별 topic mix와 repo별 topic mix를 비교합니다.',
       '["github.push-events.v1"]', 4,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-push-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-create-api', 'listing-github-create-events', 'github.create-events.v1', 'api',
       'Dataset API', 'Builder signal metadata와 최신 검증 시점을 확인합니다.',
       '/api/catalog/datasets/github.create-events.v1', NULL, '["github.create-events.v1"]', 1,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-create-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-create-sql', 'listing-github-create-events', 'github.create-events.v1', 'sql',
       'Builder launch SQL', 'repository creation만 골라 builder launch를 확인합니다.',
       NULL,
       'SELECT base_date, repo_name, user_login FROM dl_create_events WHERE organization = ''pseudolab'' AND is_repo_creation = 1 ORDER BY base_date DESC LIMIT 30;',
       '["github.create-events.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-create-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-create-followthrough-guide', 'listing-github-create-events', 'github.create-events.v1', 'documentation',
       'Builder follow-through guide', 'repo 생성 이후 첫 활성화까지 이어 보는 방법을 설명합니다.',
       NULL,
       '1. dl_create_events에서 is_repo_creation = 1 인 row를 찾습니다.
2. 같은 repo_name을 기준으로 dl_push_events, dl_pull_request_events 후속 활동을 조회합니다.
3. 필요하면 enriched/commits/... 와 enriched/pr-files/... 로 내려가 실제 첫 기여 내용을 확인합니다.
4. 생성만 있었는지, 실제 launch 이후 활성화가 있었는지 구분합니다.',
       '["github.create-events.v1","github.push-events.v1","github.pull-request-events.v1"]', 3,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-create-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-watch-api', 'listing-github-watch-events', 'github.watch-events.v1', 'api',
       'Dataset API', 'Support signal metadata와 최신 검증 시점을 확인합니다.',
       '/api/catalog/datasets/github.watch-events.v1', NULL, '["github.watch-events.v1"]', 1,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-watch-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-watch-sql', 'listing-github-watch-events', 'github.watch-events.v1', 'sql',
       'Weighted interest SQL', '내부/외부 관심을 가중치로 분리해 확인합니다.',
       NULL,
       'WITH internal_logins AS ( SELECT member_login AS user_login FROM dl_member_events WHERE is_member_added = 1 AND member_login IS NOT NULL UNION SELECT user_login FROM dl_push_events UNION SELECT user_login FROM dl_pull_request_events UNION SELECT pr_author_login AS user_login FROM dl_pull_request_events WHERE pr_author_login IS NOT NULL UNION SELECT reviewer_login AS user_login FROM dl_pull_request_review_events WHERE reviewer_login IS NOT NULL UNION SELECT commenter_login AS user_login FROM dl_pull_request_review_comment_events WHERE commenter_login IS NOT NULL ) SELECT w.repo_name, COUNT(*) FILTER (WHERE i.user_login IS NOT NULL) AS internal_watch_count, COUNT(*) FILTER (WHERE i.user_login IS NULL) AS external_watch_count, COUNT(*) FILTER (WHERE i.user_login IS NOT NULL) * 2 + COUNT(*) FILTER (WHERE i.user_login IS NULL) AS weighted_interest_score FROM dl_watch_events w LEFT JOIN internal_logins i ON i.user_login = w.user_login WHERE w.organization = ''pseudolab'' GROUP BY w.repo_name ORDER BY weighted_interest_score DESC, w.repo_name ASC LIMIT 30;',
       '["github.watch-events.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-watch-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-watch-conversion-guide', 'listing-github-watch-events', 'github.watch-events.v1', 'documentation',
       'Interest-to-contribution guide', '관심 신호와 실제 기여 전환을 함께 해석하는 방법을 설명합니다.',
       NULL,
       '1. dl_watch_events에서 관심도가 높은 repo를 찾습니다.
2. 같은 repo에 대해 dl_push_events, dl_pull_request_events, dl_pull_request_review_events를 함께 조회합니다.
3. 관심은 높지만 후속 기여가 적은 repo와, 관심과 기여가 함께 높은 repo를 구분합니다.
4. support signal은 enrich detail보다 contribution dataset과의 조합 해석이 더 중요합니다.',
       '["github.watch-events.v1","github.push-events.v1","github.pull-request-events.v1"]', 3,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-watch-events');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-pr-sql', 'listing-github-pull-request-events-v1', 'github.pull-request-events.v1', 'sql',
       'Recent PR candidates SQL', '최근 PR 후보를 찾아 file-level enrich 분석으로 연결합니다.',
       NULL,
       'SELECT base_date, repo_name, pr_number, pr_title, action, pr_author_login FROM dl_pull_request_events WHERE organization = ''pseudolab'' ORDER BY base_date DESC, pr_number DESC LIMIT 30;',
       '["github.pull-request-events.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-pull-request-events-v1');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-pr-files-guide', 'listing-github-pull-request-events-v1', 'github.pull-request-events.v1', 'documentation',
       'PR file enrich guide', 'PR 후보에서 changed files detail로 내려가는 방법을 설명합니다.',
       NULL,
       '1. dl_pull_request_events에서 repo_name, pr_number 후보를 찾습니다.
2. repo_name을 owner/repo로 분리합니다.
3. github-archive-raw/enriched/pr-files/{owner}/{repo}/{pr_number}.json 경로에서 파일 변경 detail을 조회합니다.
4. docs/app/infra/experiment 같은 파일 영역 기준으로 PR 성격을 분류합니다.',
       '["github.pull-request-events.v1"]', 3,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-pull-request-events-v1');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-review-sql', 'listing-github-pull-request-review-events-v1', 'github.pull-request-review-events.v1', 'sql',
       'Reviewer activity SQL', '최근 reviewer contribution 후보를 조회합니다.',
       NULL,
       'SELECT base_date, repo_name, pr_number, reviewer_login, state FROM dl_pull_request_review_events WHERE organization = ''pseudolab'' ORDER BY base_date DESC, pr_number DESC LIMIT 30;',
       '["github.pull-request-review-events.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-pull-request-review-events-v1');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-review-guide', 'listing-github-pull-request-review-events-v1', 'github.pull-request-review-events.v1', 'documentation',
       'PR review enrich guide', 'review event와 review detail payload를 함께 읽는 방법을 설명합니다.',
       NULL,
       '1. dl_pull_request_review_events에서 repo_name, pr_number, reviewer_login 후보를 찾습니다.
2. github-archive-raw/enriched/pr-reviews/{owner}/{repo}/{pr_number}.json 으로 review payload를 조회합니다.
3. reviewer별 승인/코멘트 패턴과 반복적으로 등장하는 피드백 주제를 정리합니다.',
       '["github.pull-request-review-events.v1"]', 3,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-pull-request-review-events-v1');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-review-comment-sql', 'listing-github-pull-request-review-comment-events-v1', 'github.pull-request-review-comment-events.v1', 'sql',
       'Review hotspot SQL', 'diff_hunk 기준 review hotspot 후보를 확인합니다.',
       NULL,
       'SELECT base_date, repo_name, pr_number, commenter_login, file_path, diff_hunk FROM dl_pull_request_review_comment_events WHERE organization = ''pseudolab'' ORDER BY base_date DESC, pr_number DESC LIMIT 30;',
       '["github.pull-request-review-comment-events.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-pull-request-review-comment-events-v1');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-review-comment-guide', 'listing-github-pull-request-review-comment-events-v1', 'github.pull-request-review-comment-events.v1', 'documentation',
       'Diff-hunk + PR files guide', 'review comment를 changed files detail과 함께 읽는 방법을 설명합니다.',
       NULL,
       '1. dl_pull_request_review_comment_events에서 file_path, diff_hunk, pr_number 후보를 찾습니다.
2. github-archive-raw/enriched/pr-files/{owner}/{repo}/{pr_number}.json 에서 전체 changed files를 조회합니다.
3. diff_hunk와 file_path를 대조해 어떤 코드 영역이 집중 피드백을 받았는지 요약합니다.
4. 필요하면 enriched/pr-reviews/... 를 함께 읽어 승인/수정 맥락을 보강합니다.',
       '["github.pull-request-review-comment-events.v1","github.pull-request-events.v1"]', 3,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-pull-request-review-comment-events-v1');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-repo-api', 'listing-github-repo', 'ds.github.repo.v1', 'api',
       'Dataset API', 'Catalog metadata와 최신 검증 시점을 확인합니다.',
       '/api/catalog/datasets/ds.github.repo.v1', NULL, '["ds.github.repo.v1"]', 1,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-repo')
  AND EXISTS (SELECT 1 FROM catalog_datasets WHERE id = 'ds.github.repo.v1');

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT 'resource-github-repo-guide', 'listing-github-repo', 'ds.github.repo.v1', 'documentation',
       'Ownership audit guide', '프로젝트 포트폴리오와 ownership 검토 지침입니다.',
       NULL,
       'Review repository inventory for study/research portfolio scope, ownership, and coverage.',
       '["ds.github.repo.v1"]', 2,
       '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z'
WHERE EXISTS (SELECT 1 FROM marketplace_listings WHERE id = 'listing-github-repo')
  AND EXISTS (SELECT 1 FROM catalog_datasets WHERE id = 'ds.github.repo.v1');
