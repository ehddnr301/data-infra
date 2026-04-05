INSERT INTO listing_owners
  (id, slug, display_name, team_name, role_title, bio, avatar_url, contact_email, slack_channel, created_at, updated_at)
VALUES
  ('owner-pseudolab', 'pseudolab-data', 'PseudoLab Data Team', 'Data Platform', 'Domain owner',
   'PseudoLab Supabase 데이터를 운영하는 내부 owner.', NULL,
   'pseudolab-data@pseudolab.org', '#pseudolab-data',
   '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')
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
