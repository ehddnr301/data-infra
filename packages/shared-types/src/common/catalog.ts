import type { IsoDateTime, JsonText } from './scalars'

export type DomainName = 'github' | 'discord' | 'linkedin' | 'members'

// D1 catalog_datasets 테이블 Row
export type CatalogDataset = {
  id: string
  domain: DomainName
  name: string
  description: string
  schema_json: JsonText | null // JSON-LD T-Box
  lineage_json: JsonText | null
  owner: string | null
  tags: string | null // comma-separated 또는 JSON array
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export type GlossaryTerm = {
  id: string
  domain: DomainName
  term: string
  definition: string
  related_terms: string[]
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export type LineageNodeData = {
  datasetId: string
  label?: string
  domain?: DomainName | string
}

export type LineageEdgeData = {
  step?: string
}

export type LineageNode = {
  id: string
  type: 'dataset'
  position: {
    x: number
    y: number
  }
  data: LineageNodeData
}

export type LineageEdge = {
  id: string
  source: string
  target: string
  data?: LineageEdgeData
  label?: string
}

export type LineageGraph = {
  version: 1
  nodes: LineageNode[]
  edges: LineageEdge[]
}

export type LineageViewport = {
  x: number
  y: number
  zoom: number
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

export type DatasetPreviewResponse = {
  datasetId: string
  source: {
    kind: 'mapped-table' | 'unmapped'
    table: string | null
  }
  columns: string[]
  rows: Array<Record<string, unknown>>
  meta: {
    limit: number
    returned: number
    reason?: 'dataset-not-mapped' | 'empty-source'
  }
}

export type SearchType = 'all' | 'dataset' | 'column' | 'glossary'

export type DatasetSearchHit = {
  id: string
  domain: DomainName
  name: string
  description: string
  updated_at: IsoDateTime
}

export type ColumnSearchHit = {
  dataset_id: string
  dataset_name: string
  domain: DomainName
  column_name: string
  data_type: string
  description: string | null
  is_pii: boolean
}

export type GlossarySearchHit = {
  id: string
  domain: DomainName
  term: string
  definition: string
  updated_at: IsoDateTime
}

export type SearchGroup<T> = {
  total: number
  items: T[]
}

export type IntegratedSearchResult = {
  query: string
  type: SearchType
  groups: {
    datasets: SearchGroup<DatasetSearchHit>
    columns: SearchGroup<ColumnSearchHit>
    glossary: SearchGroup<GlossarySearchHit>
  }
}
