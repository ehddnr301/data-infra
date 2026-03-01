CREATE TABLE IF NOT EXISTS glossary_backfill_conflicts (
  domain TEXT NOT NULL,
  term TEXT NOT NULL,
  dataset_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  logged_at TEXT NOT NULL CHECK (logged_at GLOB '????-??-??T??:??:??*')
);

INSERT INTO glossary_backfill_conflicts (domain, term, dataset_id, reason, logged_at)
SELECT
  d.domain,
  j.key,
  d.id,
  'duplicate-in-source',
  strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
FROM catalog_datasets d
JOIN json_each(d.glossary_json) j
WHERE d.glossary_json IS NOT NULL
  AND json_valid(d.glossary_json)
  AND json_type(d.glossary_json) = 'object'
  AND (
    SELECT COUNT(*)
    FROM catalog_datasets d2
    JOIN json_each(d2.glossary_json) j2
      ON d2.glossary_json IS NOT NULL
      AND json_valid(d2.glossary_json)
      AND json_type(d2.glossary_json) = 'object'
      AND d2.domain = d.domain
      AND j2.key = j.key
  ) > 1;

INSERT INTO glossary_backfill_conflicts (domain, term, dataset_id, reason, logged_at)
SELECT
  d.domain,
  j.key,
  d.id,
  'already-exists',
  strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
FROM catalog_datasets d
JOIN json_each(d.glossary_json) j
WHERE d.glossary_json IS NOT NULL
  AND json_valid(d.glossary_json)
  AND json_type(d.glossary_json) = 'object'
  AND EXISTS (
    SELECT 1
    FROM glossary_terms gt
    WHERE gt.domain = d.domain
      AND gt.term = j.key
  );

INSERT INTO glossary_terms (id, domain, term, definition, related_terms, created_at, updated_at)
SELECT
  lower(
    substr(hex(randomblob(4)), 1, 8) || '-' ||
    substr(hex(randomblob(2)), 1, 4) || '-' ||
    '7' || substr(hex(randomblob(2)), 2, 3) || '-' ||
    substr('89ab', (abs(random()) % 4) + 1, 1) || substr(hex(randomblob(2)), 2, 3) || '-' ||
    substr(hex(randomblob(6)), 1, 12)
  ) AS id,
  d.domain,
  j.key AS term,
  CAST(j.value AS TEXT) AS definition,
  '[]' AS related_terms,
  strftime('%Y-%m-%dT%H:%M:%fZ', 'now') AS created_at,
  strftime('%Y-%m-%dT%H:%M:%fZ', 'now') AS updated_at
FROM catalog_datasets d
JOIN json_each(d.glossary_json) j
WHERE d.glossary_json IS NOT NULL
  AND json_valid(d.glossary_json)
  AND json_type(d.glossary_json) = 'object'
ON CONFLICT(domain, term) DO NOTHING;
