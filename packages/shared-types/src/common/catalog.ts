import type { IsoDateTime, JsonText } from './scalars'

export const DOMAIN_NAMES = ['github', 'discord', 'linkedin', 'members', 'pseudolab'] as const
export type DomainName = (typeof DOMAIN_NAMES)[number]

export const MARKETPLACE_DOMAIN_LABELS: Record<DomainName, string> = {
  github: 'GitHub',
  discord: 'Discord',
  linkedin: 'LinkedIn',
  members: 'Members',
  pseudolab: 'PseudoLab',
}

export const MARKETPLACE_DOMAIN_DESCRIPTIONS: Record<DomainName, string> = {
  github:
    'gharchive.org and GitHub REST API daily batches for repository activity, builder launches, and community interest across PseudoLab projects.',
  discord:
    'Privacy-aware Discord Bot/API batches for community messages and collector health, focused on public study channels and excluding DMs.',
  linkedin: 'Professional network datasets reserved for future marketplace expansion.',
  members: 'Member relationship datasets reserved for future marketplace expansion.',
  pseudolab:
    'PseudoLab Supabase 운영 데이터의 daily snapshot/incremental 적재. 프로젝트, 이벤트, 사용자 프로필, 커뮤니티 활동 등 79개 테이블.',
}

export function isDomainName(value: string): value is DomainName {
  return DOMAIN_NAMES.includes(value as DomainName)
}

export function normalizeDomainName(value: string): DomainName | null {
  const normalized = value.trim().toLowerCase()
  return isDomainName(normalized) ? normalized : null
}

export function parseJsonTextArray(raw: JsonText | string | null | undefined): string[] {
  if (typeof raw !== 'string' || raw.trim().length === 0) {
    return []
  }

  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === 'string')
      : []
  } catch {
    return []
  }
}

export function parseTagList(raw: string | null | undefined): string[] {
  if (typeof raw !== 'string' || raw.trim().length === 0) {
    return []
  }

  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) {
      return parsed.filter((item): item is string => typeof item === 'string')
    }
  } catch {
    // fall through to comma-separated parsing
  }

  return raw
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function getMarketplaceListingSlug(input: {
  datasetId: string
  domain: DomainName
}): string {
  const prefix = `${input.domain}.`
  return input.datasetId.startsWith(prefix) ? input.datasetId.slice(prefix.length) : input.datasetId
}

export function getMarketplaceListingRouteParams(input: {
  datasetId: string
  domain: DomainName
}): {
  domain: DomainName
  listingSlug: string
} {
  return {
    domain: input.domain,
    listingSlug: getMarketplaceListingSlug(input),
  }
}

export type MarketplaceListingRef = {
  domain: DomainName
  slug: string
  path: string
}

export function getMarketplaceListingPath(input: {
  datasetId: string
  domain: DomainName
}): string {
  const params = getMarketplaceListingRouteParams(input)
  return `/listings/${params.domain}/${params.listingSlug}`
}

export function getMarketplaceListingRef(input: {
  datasetId: string
  domain?: DomainName
}): MarketplaceListingRef | null {
  if (!input.domain) {
    return null
  }

  const slug = getMarketplaceListingSlug({
    datasetId: input.datasetId,
    domain: input.domain,
  })

  return {
    domain: input.domain,
    slug,
    path: `/listings/${input.domain}/${slug}`,
  }
}

export function getMarketplaceDomainPath(domain: DomainName): string {
  return `/domains/${domain}`
}

// D1 catalog_datasets 테이블 Row
export type CatalogDatasetRow = {
  id: string
  domain: DomainName
  name: string
  description: string
  schema_json: JsonText | null // JSON-LD T-Box
  lineage_json: JsonText | null
  owner: string | null
  tags: string | null // comma-separated 또는 JSON array
  purpose: string | null
  limitations: JsonText | null
  usage_examples: JsonText | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export type CatalogDataset = {
  id: string
  domain: DomainName
  name: string
  description: string
  schema_json: JsonText | null // JSON-LD T-Box
  lineage_json: JsonText | null
  owner: string | null
  tags: string | null // comma-separated 또는 JSON array
  purpose: string | null
  limitations: string[]
  usage_examples: string[]
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
    total_rows: number | null
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

export type ListingResourceType = 'sql' | 'api' | 'notebook' | 'documentation'

export type ListingOwner = {
  id: string
  slug: string
  display_name: string
  team_name: string | null
  role_title: string | null
  bio: string | null
  avatar_url: string | null
  contact_email: string | null
  slack_channel: string | null
}

export type MarketplaceListingDataset = {
  id: string
  domain: DomainName
  slug: string
  name: string
  description: string
  owner: string | null
  tags: string[]
  purpose: string | null
  limitations: string[]
  usage_examples: string[]
  preview_available: boolean
  has_pii: boolean
  updated_at: IsoDateTime
}

export type ListingBusinessNeed = {
  id: string
  title: string
  summary: string
  display_order: number
}

export type ListingResource = {
  id: string
  type: ListingResourceType
  title: string
  summary: string | null
  url: string | null
  content: string | null
  display_order: number
  related_dataset_ids: string[]
}

export type MarketplaceListingSummary = {
  id: string
  dataset_id: string
  domain: DomainName
  slug: string
  title: string
  subtitle: string | null
  description: string
  category: string
  update_frequency: string | null
  coverage_summary: string | null
  documentation_url: string | null
  last_verified_at: IsoDateTime | null
  owner: ListingOwner
  business_need_tags: string[]
  preview_available: boolean
  has_pii: boolean
}

export type MarketplaceListingDetail = MarketplaceListingSummary & {
  dataset: MarketplaceListingDataset
  business_needs: ListingBusinessNeed[]
  resources: ListingResource[]
  related_listings: MarketplaceListingSummary[]
}

export type MarketplaceDomainSummary = {
  key: DomainName
  label: string
  description: string
  listing_count: number
  featured_listing_slug: string | null
  featured_listing_title: string | null
}

export type MarketplaceDomainDetail = MarketplaceDomainSummary & {
  listings: MarketplaceListingSummary[]
}
