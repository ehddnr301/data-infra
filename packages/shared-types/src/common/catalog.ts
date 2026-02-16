import type { IsoDateTime, JsonText } from './scalars'

export type DomainName = 'github' | 'discord' | 'linkedin' | 'members'

// D1 catalog_datasets 테이블 Row
export type CatalogDataset = {
  id: string
  domain: DomainName
  name: string
  description: string
  schema_json: JsonText | null // JSON-LD T-Box
  glossary_json: JsonText | null
  lineage_json: JsonText | null
  owner: string | null
  tags: string | null // comma-separated 또는 JSON array
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

// D1 catalog_columns 테이블 Row
export type CatalogColumn = {
  dataset_id: string
  column_name: string
  data_type: string
  description: string | null
  is_pii: boolean
  examples: string | null // JSON array
}
