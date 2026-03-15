INSERT OR REPLACE INTO listing_owners
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
   'members-data@pseudolab.org', '#members-data', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z');

DELETE FROM listing_resources;
DELETE FROM listing_business_needs;
DELETE FROM listing_datasets;
DELETE FROM marketplace_listings;

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
    WHEN 'github' THEN 'GitHub dataset product'
    WHEN 'discord' THEN 'Discord dataset product'
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
  cd.description AS coverage_summary,
  'internal' AS update_frequency,
  '/api/catalog/datasets/' || cd.id AS documentation_url,
  cd.updated_at AS last_verified_at,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd;

INSERT OR REPLACE INTO listing_business_needs
  (id, listing_id, title, summary, display_order)
SELECT
  'need-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')),
  'listing-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')),
  CASE cd.domain
    WHEN 'github' THEN 'Engineering activity review'
    WHEN 'discord' THEN 'Community operations review'
    WHEN 'linkedin' THEN 'LinkedIn profile review'
    ELSE 'Member health review'
  END,
  CASE cd.domain
    WHEN 'github' THEN 'Repository activity와 engineering signals를 한 곳에서 검토합니다.'
    WHEN 'discord' THEN 'Community operations와 moderation signals를 한 곳에서 검토합니다.'
    WHEN 'linkedin' THEN 'LinkedIn-facing datasets를 위한 future workflow placeholder입니다.'
    ELSE 'Member-facing datasets를 위한 future workflow placeholder입니다.'
  END,
  1
FROM catalog_datasets cd;

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
FROM catalog_datasets cd;

INSERT OR REPLACE INTO listing_resources
  (id, listing_id, dataset_id, resource_type, title, summary, url, content, related_dataset_ids, display_order, created_at, updated_at)
SELECT
  'resource-preview-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')),
  'listing-' || LOWER(REPLACE(REPLACE(CASE WHEN cd.id LIKE 'ds.%' THEN substr(cd.id, 4) ELSE cd.id END, '.', '-'), '_', '-')),
  cd.id,
  'api',
  'Preview API',
  'Dataset preview endpoint를 바로 호출합니다.',
  '/api/catalog/datasets/' || cd.id || '/preview',
  NULL,
  json_array(cd.id),
  2,
  cd.created_at,
  cd.updated_at
FROM catalog_datasets cd;
