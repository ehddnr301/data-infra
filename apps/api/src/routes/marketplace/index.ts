import { zValidator } from '@hono/zod-validator'
import type {
  ApiSuccess,
  DomainName,
  Env,
  ListingBusinessNeed,
  ListingOwner,
  ListingResource,
  MarketplaceDomainDetail,
  MarketplaceDomainSummary,
  MarketplaceListingDataset,
  MarketplaceListingDetail,
  MarketplaceListingSummary,
} from '@pseudolab/shared-types'
import {
  DOMAIN_NAMES,
  MARKETPLACE_DOMAIN_DESCRIPTIONS,
  MARKETPLACE_DOMAIN_LABELS,
  getMarketplaceListingSlug,
  parseJsonTextArray,
  parseTagList,
} from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { z } from 'zod'
import { notFound, validationError } from '../../lib/errors'
import { hasPreviewSource } from '../catalog/preview-sources'

const marketplaceRouter = new Hono<{ Bindings: Env }>()

const ListingIdentityParamSchema = z.object({
  domain: z.enum(DOMAIN_NAMES),
  slug: z.string().trim().min(1).max(255),
})

const DomainParamSchema = z.object({
  domain: z.enum(DOMAIN_NAMES),
})

const validate = (schema: z.ZodTypeAny, target: 'param' | 'query') =>
  zValidator(target, schema, (result) => {
    if (!result.success) {
      const detail = result.error.issues
        .map((issue) => `${issue.path.join('.') || target}: ${issue.message}`)
        .join(', ')
      throw validationError(detail)
    }
  })

type ListingRow = Record<string, unknown>
type ListingBusinessNeedRow = Record<string, unknown>
type ListingResourceRow = Record<string, unknown>

function toOptionalString(value: unknown): string | null {
  return typeof value === 'string' ? value : null
}

function toBooleanFlag(value: unknown): boolean {
  return value === 1 || value === true || value === '1'
}

function buildInClause(ids: string[]): string {
  return ids.map(() => '?').join(', ')
}

function parseRelatedIds(raw: unknown): string[] {
  return typeof raw === 'string' ? parseJsonTextArray(raw) : []
}

function mapOwner(row: ListingRow): ListingOwner {
  return {
    id: String(row.owner_id),
    slug: String(row.owner_slug),
    display_name: String(row.owner_display_name),
    team_name: toOptionalString(row.owner_team_name),
    role_title: toOptionalString(row.owner_role_title),
    bio: toOptionalString(row.owner_bio),
    avatar_url: toOptionalString(row.owner_avatar_url),
    contact_email: toOptionalString(row.owner_contact_email),
    slack_channel: toOptionalString(row.owner_slack_channel),
  }
}

function mapDataset(row: ListingRow): MarketplaceListingDataset {
  const domain = row.domain as DomainName
  const datasetId = String(row.dataset_id)

  return {
    id: datasetId,
    domain,
    slug: getMarketplaceListingSlug({ datasetId, domain }),
    name: String(row.dataset_name),
    description: String(row.dataset_description),
    owner: toOptionalString(row.dataset_owner),
    tags: parseTagList(toOptionalString(row.dataset_tags)),
    purpose: toOptionalString(row.dataset_purpose),
    limitations: parseJsonTextArray(toOptionalString(row.dataset_limitations)),
    usage_examples: parseJsonTextArray(toOptionalString(row.dataset_usage_examples)),
    preview_available: hasPreviewSource(datasetId),
    has_pii: toBooleanFlag(row.has_pii),
    updated_at: String(row.dataset_updated_at),
  }
}

function mapSummary(row: ListingRow, businessNeedTags: string[]): MarketplaceListingSummary {
  return {
    id: String(row.id),
    dataset_id: String(row.dataset_id),
    domain: row.domain as DomainName,
    slug: String(row.slug),
    title: String(row.title),
    subtitle: toOptionalString(row.subtitle),
    description: String(row.description),
    category: String(row.category),
    update_frequency: toOptionalString(row.update_frequency),
    coverage_summary: toOptionalString(row.coverage_summary),
    documentation_url: toOptionalString(row.documentation_url),
    last_verified_at: toOptionalString(row.last_verified_at),
    owner: mapOwner(row),
    business_need_tags: businessNeedTags,
    preview_available: hasPreviewSource(String(row.dataset_id)),
    has_pii: toBooleanFlag(row.has_pii),
  }
}

function mapBusinessNeed(row: ListingBusinessNeedRow): ListingBusinessNeed {
  return {
    id: String(row.id),
    title: String(row.title),
    summary: String(row.summary),
    display_order: Number(row.display_order ?? 0),
  }
}

function mapResource(row: ListingResourceRow): ListingResource {
  return {
    id: String(row.id),
    type: String(row.resource_type) as ListingResource['type'],
    title: String(row.title),
    summary: toOptionalString(row.summary),
    url: toOptionalString(row.url),
    content: toOptionalString(row.content),
    display_order: Number(row.display_order ?? 0),
    related_dataset_ids: parseRelatedIds(row.related_dataset_ids),
  }
}

async function fetchListingRows(
  db: Env['DB'],
  options?: {
    ids?: string[]
    domain?: DomainName
    excludeId?: string
    limit?: number
  },
): Promise<ListingRow[]> {
  let query = `
    SELECT
      ml.id,
      ml.dataset_id,
      ml.domain,
      ml.slug,
      ml.title,
      ml.subtitle,
      ml.description,
      ml.category,
      ml.coverage_summary,
      ml.update_frequency,
      ml.documentation_url,
      ml.last_verified_at,
      ml.created_at,
      ml.updated_at,
      cd.name AS dataset_name,
      cd.description AS dataset_description,
      cd.owner AS dataset_owner,
      cd.tags AS dataset_tags,
      cd.purpose AS dataset_purpose,
      cd.limitations AS dataset_limitations,
      cd.usage_examples AS dataset_usage_examples,
      cd.updated_at AS dataset_updated_at,
      CASE WHEN EXISTS (
        SELECT 1
        FROM catalog_columns cc
        WHERE cc.dataset_id = ml.dataset_id AND cc.is_pii = 1
      ) THEN 1 ELSE 0 END AS has_pii,
      lo.id AS owner_id,
      lo.slug AS owner_slug,
      lo.display_name AS owner_display_name,
      lo.team_name AS owner_team_name,
      lo.role_title AS owner_role_title,
      lo.bio AS owner_bio,
      lo.avatar_url AS owner_avatar_url,
      lo.contact_email AS owner_contact_email,
      lo.slack_channel AS owner_slack_channel
    FROM marketplace_listings ml
    JOIN catalog_datasets cd ON cd.id = ml.dataset_id
    JOIN listing_owners lo ON lo.id = ml.owner_id
  `

  const clauses: string[] = []
  const bindings: Array<string | number> = []

  if (options?.ids && options.ids.length > 0) {
    clauses.push(`ml.id IN (${buildInClause(options.ids)})`)
    bindings.push(...options.ids)
  }

  if (options?.domain) {
    clauses.push('ml.domain = ?')
    bindings.push(options.domain)
  }

  if (options?.excludeId) {
    clauses.push('ml.id != ?')
    bindings.push(options.excludeId)
  }

  if (clauses.length > 0) {
    query += ` WHERE ${clauses.join(' AND ')}`
  }

  query +=
    ' ORDER BY ml.domain ASC, COALESCE(ml.last_verified_at, cd.updated_at) DESC, ml.title ASC'

  if (options?.limit) {
    query += ' LIMIT ?'
    bindings.push(options.limit)
  }

  const rows = await db
    .prepare(query)
    .bind(...bindings)
    .all<ListingRow>()
  return rows.results
}

async function fetchListingRowByIdentity(
  db: Env['DB'],
  input: { domain: DomainName; slug: string },
): Promise<ListingRow | null> {
  const row = await db
    .prepare(
      `SELECT
        ml.id,
        ml.dataset_id,
        ml.domain,
        ml.slug,
        ml.title,
        ml.subtitle,
        ml.description,
        ml.category,
        ml.coverage_summary,
        ml.update_frequency,
        ml.documentation_url,
        ml.last_verified_at,
        ml.created_at,
        ml.updated_at,
        cd.name AS dataset_name,
        cd.description AS dataset_description,
        cd.owner AS dataset_owner,
        cd.tags AS dataset_tags,
        cd.purpose AS dataset_purpose,
        cd.limitations AS dataset_limitations,
        cd.usage_examples AS dataset_usage_examples,
        cd.updated_at AS dataset_updated_at,
        CASE WHEN EXISTS (
          SELECT 1
          FROM catalog_columns cc
          WHERE cc.dataset_id = ml.dataset_id AND cc.is_pii = 1
        ) THEN 1 ELSE 0 END AS has_pii,
        lo.id AS owner_id,
        lo.slug AS owner_slug,
        lo.display_name AS owner_display_name,
        lo.team_name AS owner_team_name,
        lo.role_title AS owner_role_title,
        lo.bio AS owner_bio,
        lo.avatar_url AS owner_avatar_url,
        lo.contact_email AS owner_contact_email,
        lo.slack_channel AS owner_slack_channel
      FROM marketplace_listings ml
      JOIN catalog_datasets cd ON cd.id = ml.dataset_id
      JOIN listing_owners lo ON lo.id = ml.owner_id
      WHERE ml.domain = ? AND ml.slug = ?
      LIMIT 1`,
    )
    .bind(input.domain, input.slug)
    .first<ListingRow>()

  return row
}

async function fetchBusinessNeedMap(
  db: Env['DB'],
  listingIds: string[],
): Promise<Map<string, ListingBusinessNeed[]>> {
  const result = new Map<string, ListingBusinessNeed[]>()
  if (listingIds.length === 0) {
    return result
  }

  const rows = await db
    .prepare(
      `SELECT id, listing_id, title, summary, display_order
       FROM listing_business_needs
       WHERE listing_id IN (${buildInClause(listingIds)})
       ORDER BY listing_id ASC, display_order ASC, title ASC`,
    )
    .bind(...listingIds)
    .all<ListingBusinessNeedRow>()

  for (const row of rows.results) {
    const listingId = String(row.listing_id)
    const current = result.get(listingId) ?? []
    current.push(mapBusinessNeed(row))
    result.set(listingId, current)
  }

  return result
}

async function fetchListingResources(db: Env['DB'], listingId: string): Promise<ListingResource[]> {
  const rows = await db
    .prepare(
      `SELECT id, resource_type, title, summary, url, content, related_dataset_ids, display_order
       FROM listing_resources
       WHERE listing_id = ?
       ORDER BY display_order ASC, title ASC`,
    )
    .bind(listingId)
    .all<ListingResourceRow>()

  return rows.results.map(mapResource)
}

function buildDomainSummary(
  domain: DomainName,
  listings: MarketplaceListingSummary[],
): MarketplaceDomainSummary {
  return {
    key: domain,
    label: MARKETPLACE_DOMAIN_LABELS[domain],
    description: MARKETPLACE_DOMAIN_DESCRIPTIONS[domain],
    listing_count: listings.length,
    featured_listing_slug: listings[0]?.slug ?? null,
    featured_listing_title: listings[0]?.title ?? null,
  }
}

marketplaceRouter.get('/listings', async (c) => {
  const rows = await fetchListingRows(c.env.DB)
  const businessNeedMap = await fetchBusinessNeedMap(
    c.env.DB,
    rows.map((row) => String(row.id)),
  )

  const data: MarketplaceListingSummary[] = rows.map((row) =>
    mapSummary(
      row,
      (businessNeedMap.get(String(row.id)) ?? []).map((need) => need.title),
    ),
  )

  return c.json<ApiSuccess<MarketplaceListingSummary[]>>({ success: true, data })
})

marketplaceRouter.get(
  '/listings/:domain/:slug',
  validate(ListingIdentityParamSchema, 'param'),
  async (c) => {
    const { domain, slug } = c.req.valid('param')
    const row = await fetchListingRowByIdentity(c.env.DB, { domain, slug })

    if (!row) {
      throw notFound(`Marketplace listing not found for ${domain}/${slug}`)
    }

    const businessNeeds =
      (await fetchBusinessNeedMap(c.env.DB, [String(row.id)])).get(String(row.id)) ?? []
    const resources = await fetchListingResources(c.env.DB, String(row.id))
    const relatedRows = await fetchListingRows(c.env.DB, {
      domain,
      excludeId: String(row.id),
      limit: 3,
    })
    const relatedNeedMap = await fetchBusinessNeedMap(
      c.env.DB,
      relatedRows.map((item) => String(item.id)),
    )

    const detail: MarketplaceListingDetail = {
      ...mapSummary(
        row,
        businessNeeds.map((need) => need.title),
      ),
      dataset: mapDataset(row),
      business_needs: businessNeeds,
      resources,
      related_listings: relatedRows.map((item) =>
        mapSummary(
          item,
          (relatedNeedMap.get(String(item.id)) ?? []).map((need) => need.title),
        ),
      ),
    }

    return c.json<ApiSuccess<MarketplaceListingDetail>>({ success: true, data: detail })
  },
)

marketplaceRouter.get('/domains', async (c) => {
  const rows = await fetchListingRows(c.env.DB)
  const businessNeedMap = await fetchBusinessNeedMap(
    c.env.DB,
    rows.map((row) => String(row.id)),
  )
  const listings = rows.map((row) =>
    mapSummary(
      row,
      (businessNeedMap.get(String(row.id)) ?? []).map((need) => need.title),
    ),
  )

  const data: MarketplaceDomainSummary[] = DOMAIN_NAMES.map((domain) =>
    buildDomainSummary(
      domain,
      listings.filter((listing) => listing.domain === domain),
    ),
  )

  return c.json<ApiSuccess<MarketplaceDomainSummary[]>>({ success: true, data })
})

marketplaceRouter.get('/domains/:domain', validate(DomainParamSchema, 'param'), async (c) => {
  const { domain } = c.req.valid('param')
  const rows = await fetchListingRows(c.env.DB, { domain })
  const businessNeedMap = await fetchBusinessNeedMap(
    c.env.DB,
    rows.map((row) => String(row.id)),
  )
  const listings = rows.map((row) =>
    mapSummary(
      row,
      (businessNeedMap.get(String(row.id)) ?? []).map((need) => need.title),
    ),
  )

  const detail: MarketplaceDomainDetail = {
    ...buildDomainSummary(domain, listings),
    listings,
  }

  return c.json<ApiSuccess<MarketplaceDomainDetail>>({ success: true, data: detail })
})

marketplaceRouter.get('/health/identities', async (c) => {
  const rows = await fetchListingRows(c.env.DB)
  const mismatches = rows
    .map((row) => ({
      id: String(row.id),
      dataset_id: String(row.dataset_id),
      expected_slug: getMarketplaceListingSlug({
        datasetId: String(row.dataset_id),
        domain: row.domain as DomainName,
      }),
      actual_slug: String(row.slug),
      domain: row.domain as DomainName,
    }))
    .filter((row) => row.expected_slug !== row.actual_slug)

  return c.json({
    success: true,
    data: {
      checked: rows.length,
      mismatches,
    },
  })
})

export default marketplaceRouter
