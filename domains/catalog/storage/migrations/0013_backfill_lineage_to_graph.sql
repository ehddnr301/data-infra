WITH legacy_targets AS (
  SELECT
    id,
    domain,
    name,
    lineage_json,
    CASE
      WHEN json_type(lineage_json, '$.process') = 'array'
           AND json_array_length(json_extract(lineage_json, '$.process')) > 0
           AND json_type(lineage_json, '$.process[0]') = 'text'
      THEN json_extract(lineage_json, '$.process[0]')
      ELSE NULL
    END AS step_label
  FROM catalog_datasets
  WHERE lineage_json IS NOT NULL
    AND json_valid(lineage_json)
    AND json_type(lineage_json) = 'object'
    AND json_type(lineage_json, '$.nodes') IS NULL
    AND json_type(lineage_json, '$.edges') IS NULL
    AND (
      json_type(lineage_json, '$.upstream') = 'array'
      OR json_type(lineage_json, '$.process') = 'array'
      OR json_type(lineage_json, '$.downstream') = 'array'
    )
),
upstream_items AS (
  SELECT
    t.id AS dataset_id,
    CAST(u.key AS INTEGER) AS ord,
    CASE
      WHEN u.type = 'text' THEN CAST(u.value AS TEXT)
      ELSE COALESCE(
        CAST(json_extract(u.value, '$.datasetId') AS TEXT),
        CAST(json_extract(u.value, '$.id') AS TEXT),
        CAST(json_extract(u.value, '$.dataset_id') AS TEXT)
      )
    END AS linked_dataset_id,
    CASE
      WHEN u.type = 'object' THEN CAST(json_extract(u.value, '$.label') AS TEXT)
      ELSE NULL
    END AS linked_label,
    CASE
      WHEN u.type = 'object' THEN CAST(json_extract(u.value, '$.domain') AS TEXT)
      ELSE NULL
    END AS linked_domain
  FROM legacy_targets t
  JOIN json_each(COALESCE(json_extract(t.lineage_json, '$.upstream'), '[]')) u
),
downstream_items AS (
  SELECT
    t.id AS dataset_id,
    CAST(d.key AS INTEGER) AS ord,
    CASE
      WHEN d.type = 'text' THEN CAST(d.value AS TEXT)
      ELSE COALESCE(
        CAST(json_extract(d.value, '$.datasetId') AS TEXT),
        CAST(json_extract(d.value, '$.id') AS TEXT),
        CAST(json_extract(d.value, '$.dataset_id') AS TEXT)
      )
    END AS linked_dataset_id,
    CASE
      WHEN d.type = 'object' THEN CAST(json_extract(d.value, '$.label') AS TEXT)
      ELSE NULL
    END AS linked_label,
    CASE
      WHEN d.type = 'object' THEN CAST(json_extract(d.value, '$.domain') AS TEXT)
      ELSE NULL
    END AS linked_domain
  FROM legacy_targets t
  JOIN json_each(COALESCE(json_extract(t.lineage_json, '$.downstream'), '[]')) d
),
node_candidates AS (
  SELECT
    t.id AS dataset_id,
    t.id AS node_id,
    t.name AS node_label,
    t.domain AS node_domain,
    0 AS x,
    0 AS y,
    0 AS sort_group,
    0 AS sort_ord
  FROM legacy_targets t
  UNION ALL
  SELECT
    u.dataset_id,
    u.linked_dataset_id AS node_id,
    COALESCE(u.linked_label, u.linked_dataset_id) AS node_label,
    u.linked_domain AS node_domain,
    -300 AS x,
    (u.ord + 1) * 120 AS y,
    1 AS sort_group,
    u.ord AS sort_ord
  FROM upstream_items u
  WHERE u.linked_dataset_id IS NOT NULL AND LENGTH(u.linked_dataset_id) > 0
  UNION ALL
  SELECT
    d.dataset_id,
    d.linked_dataset_id AS node_id,
    COALESCE(d.linked_label, d.linked_dataset_id) AS node_label,
    d.linked_domain AS node_domain,
    300 AS x,
    -(d.ord + 1) * 120 AS y,
    2 AS sort_group,
    d.ord AS sort_ord
  FROM downstream_items d
  WHERE d.linked_dataset_id IS NOT NULL AND LENGTH(d.linked_dataset_id) > 0
),
dedup_nodes AS (
  SELECT
    dataset_id,
    node_id,
    MIN(node_label) AS node_label,
    MIN(node_domain) AS node_domain,
    MIN(x) AS x,
    MIN(y) AS y,
    MIN(sort_group) AS sort_group,
    MIN(sort_ord) AS sort_ord
  FROM node_candidates
  GROUP BY dataset_id, node_id
),
edges AS (
  SELECT
    t.id AS dataset_id,
    u.linked_dataset_id AS source_id,
    t.id AS target_id,
    t.step_label AS step_label,
    0 AS sort_group,
    u.ord AS sort_ord
  FROM legacy_targets t
  JOIN upstream_items u ON u.dataset_id = t.id
  WHERE u.linked_dataset_id IS NOT NULL AND LENGTH(u.linked_dataset_id) > 0
  UNION ALL
  SELECT
    t.id AS dataset_id,
    t.id AS source_id,
    d.linked_dataset_id AS target_id,
    t.step_label AS step_label,
    1 AS sort_group,
    d.ord AS sort_ord
  FROM legacy_targets t
  JOIN downstream_items d ON d.dataset_id = t.id
  WHERE d.linked_dataset_id IS NOT NULL AND LENGTH(d.linked_dataset_id) > 0
),
graph_payloads AS (
  SELECT
    t.id AS dataset_id,
    json_object(
      'version',
      1,
      'nodes',
      (
        SELECT COALESCE(json_group_array(json(node_json)), '[]')
        FROM (
          SELECT
            json_object(
              'id',
              n.node_id,
              'type',
              'dataset',
              'position',
              json_object('x', n.x, 'y', n.y),
              'data',
              json_object(
                'datasetId',
                n.node_id,
                'label',
                COALESCE(n.node_label, n.node_id),
                'domain',
                n.node_domain
              )
            ) AS node_json
          FROM dedup_nodes n
          WHERE n.dataset_id = t.id
          ORDER BY n.sort_group, n.sort_ord, n.node_id
        )
      ),
      'edges',
      (
        SELECT COALESCE(json_group_array(json(edge_json)), '[]')
        FROM (
          SELECT
            json_object(
              'id',
              e.source_id || '->' || e.target_id,
              'source',
              e.source_id,
              'target',
              e.target_id,
              'data',
              CASE
                WHEN e.step_label IS NULL THEN NULL
                ELSE json_object('step', e.step_label)
              END,
              'label',
              e.step_label
            ) AS edge_json
          FROM edges e
          WHERE e.dataset_id = t.id
          ORDER BY e.sort_group, e.sort_ord, e.source_id, e.target_id
        )
      )
    ) AS graph_json
  FROM legacy_targets t
)
UPDATE catalog_datasets
SET lineage_json = (
  SELECT graph_json
  FROM graph_payloads p
  WHERE p.dataset_id = catalog_datasets.id
)
WHERE id IN (SELECT dataset_id FROM graph_payloads);

SELECT COUNT(*) AS invalid_lineage_json_rows
FROM catalog_datasets
WHERE lineage_json IS NOT NULL
  AND NOT json_valid(lineage_json);
