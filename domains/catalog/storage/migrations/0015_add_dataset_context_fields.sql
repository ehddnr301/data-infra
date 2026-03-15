ALTER TABLE catalog_datasets
  ADD COLUMN purpose TEXT;

ALTER TABLE catalog_datasets
  ADD COLUMN limitations TEXT;

ALTER TABLE catalog_datasets
  ADD COLUMN usage_examples TEXT;
