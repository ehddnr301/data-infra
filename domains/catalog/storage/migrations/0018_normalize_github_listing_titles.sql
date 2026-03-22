UPDATE marketplace_listings
SET
  title = (
    SELECT cd.name
    FROM catalog_datasets cd
    WHERE cd.id = marketplace_listings.dataset_id
  ),
  updated_at = COALESCE(
    (
      SELECT cd.updated_at
      FROM catalog_datasets cd
      WHERE cd.id = marketplace_listings.dataset_id
    ),
    updated_at
  )
WHERE dataset_id IN ('github.push-events.v1', 'github.watch-events.v1')
  AND EXISTS (
    SELECT 1
    FROM catalog_datasets cd
    WHERE cd.id = marketplace_listings.dataset_id
  );
