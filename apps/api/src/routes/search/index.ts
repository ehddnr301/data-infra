import { zValidator } from '@hono/zod-validator'
import type {
  ApiSuccess,
  ColumnSearchHit,
  DatasetSearchHit,
  DomainName,
  Env,
  GlossarySearchHit,
  IntegratedSearchResult,
  SearchType,
} from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { z } from 'zod'
import { validationError } from '../../lib/errors'

const searchRouter = new Hono<{ Bindings: Env }>()

const SearchQuerySchema = z.object({
  q: z
    .string()
    .trim()
    .min(1)
    .refine((value) => new TextEncoder().encode(value).length <= 48, {
      message: 'q must be <= 48 bytes (UTF-8)',
    }),
  type: z.enum(['all', 'dataset', 'column', 'glossary']).optional().default('all'),
  domain: z.enum(['github', 'discord', 'linkedin', 'members']).optional(),
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
})

const PREVIEW_SIZE = 5
const CACHE_TTL_SECONDS = 60

const validate = (schema: z.ZodTypeAny, target: 'query' | 'param') =>
  zValidator(target, schema, (result) => {
    if (!result.success) {
      const detail = result.error.issues
        .map((issue) => `${issue.path.join('.') || target}: ${issue.message}`)
        .join(', ')
      throw validationError(detail)
    }
  })

function makeEmptyGroups(): IntegratedSearchResult['groups'] {
  return {
    datasets: { total: 0, items: [] },
    columns: { total: 0, items: [] },
    glossary: { total: 0, items: [] },
  }
}

function normalizePage(type: SearchType, page?: number): number {
  return type === 'all' ? 1 : (page ?? 1)
}

function normalizePageSize(type: SearchType, pageSize?: number): number {
  return type === 'all' ? PREVIEW_SIZE : (pageSize ?? 20)
}

function rowTotal(row: unknown): number {
  if (typeof row !== 'object' || row === null || !('total' in row)) {
    return 0
  }

  const raw = (row as { total?: unknown }).total
  return typeof raw === 'number' ? raw : Number(raw ?? 0)
}

function toHex(bytes: ArrayBuffer): string {
  return Array.from(new Uint8Array(bytes), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function hashQuery(value: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))
  return toHex(digest)
}

function cacheKey(input: {
  type: SearchType
  domain?: DomainName
  queryHash: string
  page: number
  pageSize: number
}): string {
  return `search:v1:${input.type}:${input.domain ?? 'all'}:${input.queryHash}:${input.page}:${input.pageSize}`
}

async function queryDatasets(
  env: Env,
  options: { query: string; domain?: DomainName; limit: number; offset: number },
): Promise<{ total: number; items: DatasetSearchHit[] }> {
  const pattern = `%${options.query}%`
  const conditions = ['(name LIKE ? OR description LIKE ?)']
  const bindings: Array<string | number> = [pattern, pattern]

  if (options.domain) {
    conditions.push('domain = ?')
    bindings.push(options.domain)
  }

  const whereClause = `WHERE ${conditions.join(' AND ')}`
  const totalRow = await env.DB.prepare(
    `SELECT COUNT(*) as total FROM catalog_datasets ${whereClause}`,
  )
    .bind(...bindings)
    .first()

  const rows = await env.DB.prepare(
    `SELECT id, domain, name, description, updated_at
       FROM catalog_datasets ${whereClause}
      ORDER BY updated_at DESC
      LIMIT ? OFFSET ?`,
  )
    .bind(...bindings, options.limit, options.offset)
    .all()

  return {
    total: rowTotal(totalRow),
    items: rows.results.map(
      (row: unknown): DatasetSearchHit => ({
        id: String((row as Record<string, unknown>).id),
        domain: (row as Record<string, unknown>).domain as DomainName,
        name: String((row as Record<string, unknown>).name),
        description: String((row as Record<string, unknown>).description),
        updated_at: String((row as Record<string, unknown>).updated_at),
      }),
    ),
  }
}

async function queryColumns(
  env: Env,
  options: { query: string; domain?: DomainName; limit: number; offset: number },
): Promise<{ total: number; items: ColumnSearchHit[] }> {
  const pattern = `%${options.query}%`
  const conditions = ['(c.column_name LIKE ? OR c.description LIKE ?)']
  const bindings: Array<string | number> = [pattern, pattern]

  if (options.domain) {
    conditions.push('d.domain = ?')
    bindings.push(options.domain)
  }

  const whereClause = `WHERE ${conditions.join(' AND ')}`
  const totalRow = await env.DB.prepare(
    `SELECT COUNT(*) as total
       FROM catalog_columns c
       JOIN catalog_datasets d ON d.id = c.dataset_id
      ${whereClause}`,
  )
    .bind(...bindings)
    .first()

  const rows = await env.DB.prepare(
    `SELECT c.dataset_id, d.name AS dataset_name, d.domain, c.column_name, c.data_type, c.description, c.is_pii
       FROM catalog_columns c
       JOIN catalog_datasets d ON d.id = c.dataset_id
      ${whereClause}
      ORDER BY d.updated_at DESC, c.column_name ASC
      LIMIT ? OFFSET ?`,
  )
    .bind(...bindings, options.limit, options.offset)
    .all()

  return {
    total: rowTotal(totalRow),
    items: rows.results.map(
      (row: unknown): ColumnSearchHit => ({
        dataset_id: String((row as Record<string, unknown>).dataset_id),
        dataset_name: String((row as Record<string, unknown>).dataset_name),
        domain: (row as Record<string, unknown>).domain as DomainName,
        column_name: String((row as Record<string, unknown>).column_name),
        data_type: String((row as Record<string, unknown>).data_type),
        description:
          typeof (row as Record<string, unknown>).description === 'string'
            ? ((row as Record<string, unknown>).description as string)
            : null,
        is_pii: Boolean((row as Record<string, unknown>).is_pii),
      }),
    ),
  }
}

async function queryGlossary(
  env: Env,
  options: { query: string; domain?: DomainName; limit: number; offset: number },
): Promise<{ total: number; items: GlossarySearchHit[] }> {
  const pattern = `%${options.query}%`
  const conditions = ['(term LIKE ? OR definition LIKE ?)']
  const bindings: Array<string | number> = [pattern, pattern]

  if (options.domain) {
    conditions.push('domain = ?')
    bindings.push(options.domain)
  }

  const whereClause = `WHERE ${conditions.join(' AND ')}`
  const totalRow = await env.DB.prepare(
    `SELECT COUNT(*) as total FROM glossary_terms ${whereClause}`,
  )
    .bind(...bindings)
    .first()

  const rows = await env.DB.prepare(
    `SELECT id, domain, term, definition, updated_at
       FROM glossary_terms ${whereClause}
      ORDER BY updated_at DESC
      LIMIT ? OFFSET ?`,
  )
    .bind(...bindings, options.limit, options.offset)
    .all()

  return {
    total: rowTotal(totalRow),
    items: rows.results.map(
      (row: unknown): GlossarySearchHit => ({
        id: String((row as Record<string, unknown>).id),
        domain: (row as Record<string, unknown>).domain as DomainName,
        term: String((row as Record<string, unknown>).term),
        definition: String((row as Record<string, unknown>).definition),
        updated_at: String((row as Record<string, unknown>).updated_at),
      }),
    ),
  }
}

searchRouter.get('/', validate(SearchQuerySchema, 'query'), async (c) => {
  const startedAt = Date.now()
  const query = c.req.valid('query')
  const normalizedQuery = query.q.trim()
  const type = query.type
  const page = normalizePage(type, query.page)
  const pageSize = normalizePageSize(type, query.pageSize)
  const offset = (page - 1) * pageSize
  const queryHash = await hashQuery(normalizedQuery)

  const key = cacheKey({
    type,
    domain: query.domain,
    queryHash,
    page,
    pageSize,
  })

  let cached: ApiSuccess<IntegratedSearchResult> | null = null
  try {
    cached = (await c.env.CACHE.get(key, 'json')) as ApiSuccess<IntegratedSearchResult> | null
  } catch {
    cached = null
  }

  if (cached) {
    return c.json({
      ...cached,
      meta: {
        ...(cached.meta ?? {}),
        cache: 'hit',
        tookMs: Date.now() - startedAt,
      },
    })
  }

  const groups = makeEmptyGroups()

  if (type === 'all') {
    const [datasets, columns, glossary] = await Promise.all([
      queryDatasets(c.env, {
        query: normalizedQuery,
        domain: query.domain,
        limit: PREVIEW_SIZE,
        offset: 0,
      }),
      queryColumns(c.env, {
        query: normalizedQuery,
        domain: query.domain,
        limit: PREVIEW_SIZE,
        offset: 0,
      }),
      queryGlossary(c.env, {
        query: normalizedQuery,
        domain: query.domain,
        limit: PREVIEW_SIZE,
        offset: 0,
      }),
    ])

    groups.datasets = datasets
    groups.columns = columns
    groups.glossary = glossary
  }

  if (type === 'dataset') {
    groups.datasets = await queryDatasets(c.env, {
      query: normalizedQuery,
      domain: query.domain,
      limit: pageSize,
      offset,
    })
  }

  if (type === 'column') {
    groups.columns = await queryColumns(c.env, {
      query: normalizedQuery,
      domain: query.domain,
      limit: pageSize,
      offset,
    })
  }

  if (type === 'glossary') {
    groups.glossary = await queryGlossary(c.env, {
      query: normalizedQuery,
      domain: query.domain,
      limit: pageSize,
      offset,
    })
  }

  const response: ApiSuccess<IntegratedSearchResult> = {
    success: true,
    data: {
      query: normalizedQuery,
      type,
      groups,
    },
    meta: {
      cache: 'miss',
      tookMs: Date.now() - startedAt,
    },
  }

  try {
    await c.env.CACHE.put(key, JSON.stringify(response), {
      expirationTtl: CACHE_TTL_SECONDS,
    })
  } catch {
    return c.json(response)
  }

  return c.json(response)
})

export default searchRouter
