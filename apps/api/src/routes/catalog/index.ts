import { zValidator } from '@hono/zod-validator'
import type {
  ApiSuccess,
  CatalogColumn,
  CatalogDataset,
  DatasetPreviewResponse,
  Env,
  GlossaryTerm,
  LineageGraph,
  PaginatedResponse,
} from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { z } from 'zod'
import { AppError, notFound, validationError } from '../../lib/errors'

const catalogRouter = new Hono<{ Bindings: Env }>()

const DatasetQuerySchema = z.object({
  domain: z.string().optional(),
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
})

const UUID_V7_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

const GlossaryQuerySchema = z.object({
  domain: z.enum(['github', 'discord', 'linkedin', 'members']).optional(),
  q: z.string().trim().min(1).optional(),
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
})

const GlossaryIdParamSchema = z.object({
  id: z.string().regex(UUID_V7_REGEX, 'id must be a valid UUIDv7'),
})

const GlossaryCreateBodySchema = z.object({
  domain: z.enum(['github', 'discord', 'linkedin', 'members']),
  term: z.string().trim().min(1).max(120),
  definition: z.string().trim().min(1),
  related_terms: z
    .array(z.string().regex(UUID_V7_REGEX, 'related_terms must contain valid UUIDv7 values'))
    .max(50)
    .optional()
    .default([]),
})

const GlossaryUpdateBodySchema = z
  .object({
    term: z.string().trim().min(1).max(120).optional(),
    definition: z.string().trim().min(1).optional(),
    related_terms: z
      .array(z.string().regex(UUID_V7_REGEX, 'related_terms must contain valid UUIDv7 values'))
      .max(50)
      .optional(),
  })
  .refine(
    (input) =>
      input.term !== undefined ||
      input.definition !== undefined ||
      input.related_terms !== undefined,
    {
      message: 'At least one field must be provided',
      path: [],
    },
  )

const IdParamSchema = z.object({
  id: z.string().min(1),
})

const PreviewQuerySchema = z.object({
  limit: z.coerce.number().int().positive().max(100).optional(),
})

const PREVIEW_SOURCE_BY_DATASET_ID: Record<string, { table: string; sortCol: string }> = {
  'discord.messages.v1': {
    table: 'discord_messages',
    sortCol: 'created_at',
  },
}

const DATASET_ID_REGEX = /^[\w.-]+$/

const LineageParamSchema = z.object({
  datasetId: z.string().min(1).max(255).regex(DATASET_ID_REGEX, 'datasetId has invalid format'),
})

const LineageNodeSchema = z.object({
  id: z.string().min(1),
  type: z.literal('dataset'),
  position: z.object({
    x: z.number(),
    y: z.number(),
  }),
  data: z.object({
    datasetId: z.string().min(1),
    label: z.string().min(1).optional(),
    domain: z.string().min(1).optional(),
  }),
})

const LineageEdgeSchema = z.object({
  id: z.string().min(1),
  source: z.string().min(1),
  target: z.string().min(1),
  data: z
    .object({
      step: z.string().min(1).optional(),
    })
    .optional(),
  label: z.string().min(1).optional(),
})

const LineageGraphSchema = z.object({
  version: z.literal(1),
  nodes: z.array(LineageNodeSchema),
  edges: z.array(LineageEdgeSchema),
})

const validate = (schema: z.ZodTypeAny, target: 'query' | 'param') =>
  zValidator(target, schema, (result) => {
    if (!result.success) {
      const detail = result.error.issues
        .map((issue) => `${issue.path.join('.') || target}: ${issue.message}`)
        .join(', ')
      throw validationError(detail)
    }
  })

const validateBody = <T extends z.ZodTypeAny>(schema: T) =>
  zValidator('json', schema, (result) => {
    if (!result.success) {
      const detail = result.error.issues
        .map((issue) => `${issue.path.join('.') || 'body'}: ${issue.message}`)
        .join(', ')
      throw validationError(detail)
    }
  })

function nowIso(): string {
  return new Date().toISOString()
}

function randomHex(length: number): string {
  const bytes = new Uint8Array(Math.ceil(length / 2))
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, length)
}

function generateUuidV7(): string {
  const timestampHex = Date.now().toString(16).padStart(12, '0').slice(-12)
  const randA = randomHex(3)
  const randomByte = crypto.getRandomValues(new Uint8Array(1))[0] ?? 0
  const variantNibble = ['8', '9', 'a', 'b'][randomByte % 4] ?? '8'
  const randB = randomHex(3)
  const randC = randomHex(12)
  return `${timestampHex.slice(0, 8)}-${timestampHex.slice(8, 12)}-7${randA}-${variantNibble}${randB}-${randC}`
}

function parseRelatedTerms(raw: unknown): string[] {
  if (typeof raw !== 'string' || raw.length === 0) {
    return []
  }

  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter((value): value is string => typeof value === 'string')
  } catch {
    return []
  }
}

function mapGlossaryRow(row: Record<string, unknown>): GlossaryTerm {
  return {
    id: String(row.id),
    domain: row.domain as GlossaryTerm['domain'],
    term: String(row.term),
    definition: String(row.definition),
    related_terms: parseRelatedTerms(row.related_terms),
    created_at: String(row.created_at),
    updated_at: String(row.updated_at),
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function parseLineageJson(raw: unknown): unknown | null {
  if (typeof raw !== 'string' || raw.length === 0) {
    return null
  }

  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function buildDefaultSelfNodeGraph(dataset: {
  id: string
  name: string
  domain: string
}): LineageGraph {
  return {
    version: 1,
    nodes: [
      {
        id: dataset.id,
        type: 'dataset',
        position: { x: 0, y: 0 },
        data: {
          datasetId: dataset.id,
          label: dataset.name,
          domain: dataset.domain,
        },
      },
    ],
    edges: [],
  }
}

function legacyNodeToDatasetInfo(item: unknown): {
  datasetId: string
  label?: string
  domain?: string
} | null {
  if (typeof item === 'string' && item.length > 0) {
    return { datasetId: item, label: item }
  }

  if (!isRecord(item)) {
    return null
  }

  const datasetIdCandidates = [item.datasetId, item.id, item.dataset_id]
  const datasetId = datasetIdCandidates.find((value): value is string => typeof value === 'string')
  if (!datasetId || datasetId.length === 0) {
    return null
  }

  const label = typeof item.label === 'string' && item.label.length > 0 ? item.label : undefined
  const domain = typeof item.domain === 'string' && item.domain.length > 0 ? item.domain : undefined

  return {
    datasetId,
    label,
    domain,
  }
}

function normalizeLegacyLineageToGraph(
  input: unknown,
  dataset: {
    id: string
    name: string
    domain: string
  },
): LineageGraph | null {
  if (!isRecord(input)) {
    return null
  }

  if (Array.isArray(input.nodes) && Array.isArray(input.edges)) {
    const parsed = LineageGraphSchema.safeParse(input)
    return parsed.success ? parsed.data : null
  }

  const hasLegacyKeys =
    Array.isArray(input.upstream) || Array.isArray(input.process) || Array.isArray(input.downstream)

  if (!hasLegacyKeys) {
    return null
  }

  const upstream = Array.isArray(input.upstream) ? input.upstream : []
  const downstream = Array.isArray(input.downstream) ? input.downstream : []
  const process = Array.isArray(input.process) ? input.process : []
  const stepLabel =
    process.length > 0 && typeof process[0] === 'string' && process[0].length > 0
      ? process[0]
      : undefined

  const nodeOrder: string[] = []
  const nodeMap = new Map<
    string,
    {
      id: string
      type: 'dataset'
      position: { x: number; y: number }
      data: { datasetId: string; label?: string; domain?: string }
    }
  >()

  const pushNode = (
    info: { datasetId: string; label?: string; domain?: string },
    fallbackX: number,
  ) => {
    if (nodeMap.has(info.datasetId)) {
      return
    }

    nodeOrder.push(info.datasetId)
    nodeMap.set(info.datasetId, {
      id: info.datasetId,
      type: 'dataset',
      position: { x: fallbackX, y: 0 },
      data: {
        datasetId: info.datasetId,
        label: info.label ?? info.datasetId,
        domain: info.domain,
      },
    })
  }

  const center = { datasetId: dataset.id, label: dataset.name, domain: dataset.domain }
  pushNode(center, 0)

  for (const item of upstream) {
    const info = legacyNodeToDatasetInfo(item)
    if (info) {
      pushNode(info, -300)
    }
  }

  for (const item of downstream) {
    const info = legacyNodeToDatasetInfo(item)
    if (info) {
      pushNode(info, 300)
    }
  }

  const edges: LineageGraph['edges'] = []
  for (const item of upstream) {
    const info = legacyNodeToDatasetInfo(item)
    if (!info) {
      continue
    }

    edges.push({
      id: `${info.datasetId}->${dataset.id}`,
      source: info.datasetId,
      target: dataset.id,
      data: stepLabel ? { step: stepLabel } : undefined,
      label: stepLabel,
    })
  }

  for (const item of downstream) {
    const info = legacyNodeToDatasetInfo(item)
    if (!info) {
      continue
    }

    edges.push({
      id: `${dataset.id}->${info.datasetId}`,
      source: dataset.id,
      target: info.datasetId,
      data: stepLabel ? { step: stepLabel } : undefined,
      label: stepLabel,
    })
  }

  const nodes = nodeOrder.map((id, index) => {
    const node = nodeMap.get(id)
    if (!node) {
      return {
        id,
        type: 'dataset' as const,
        position: { x: 0, y: index * 120 },
        data: { datasetId: id, label: id },
      }
    }

    const y = node.position.x < 0 ? (index + 1) * 120 : node.position.x > 0 ? -(index + 1) * 120 : 0
    return {
      ...node,
      position: { x: node.position.x, y },
    }
  })

  const graph: LineageGraph = {
    version: 1,
    nodes,
    edges,
  }

  return graph
}

function assertLineageGraphIntegrity(graph: LineageGraph): void {
  const nodeIdSet = new Set<string>()
  for (const node of graph.nodes) {
    if (nodeIdSet.has(node.id)) {
      throw validationError(`nodes contain duplicate id: ${node.id}`)
    }
    nodeIdSet.add(node.id)
  }

  const edgeIdSet = new Set<string>()
  for (const edge of graph.edges) {
    if (edgeIdSet.has(edge.id)) {
      throw validationError(`edges contain duplicate id: ${edge.id}`)
    }
    edgeIdSet.add(edge.id)

    if (!nodeIdSet.has(edge.source) || !nodeIdSet.has(edge.target)) {
      throw validationError(`edge ${edge.id} references unknown node`)
    }
  }
}

async function assertNoDuplicateRelatedTerms(relatedTerms: string[]): Promise<void> {
  if (relatedTerms.length !== new Set(relatedTerms).size) {
    throw validationError('related_terms must not contain duplicate ids')
  }
}

async function assertRelatedTermsIntegrity(
  c: { env: Env },
  options: {
    domain: string
    targetId: string
    relatedTerms: string[]
  },
): Promise<void> {
  const { domain, targetId, relatedTerms } = options

  await assertNoDuplicateRelatedTerms(relatedTerms)

  if (relatedTerms.includes(targetId)) {
    throw validationError('related_terms must not contain self id')
  }

  if (relatedTerms.length === 0) {
    return
  }

  const placeholders = relatedTerms.map(() => '?').join(', ')
  const rows = await c.env.DB.prepare(
    `SELECT id, domain FROM glossary_terms WHERE id IN (${placeholders})`,
  )
    .bind(...relatedTerms)
    .all()

  const results = rows.results as Array<{ id: string; domain: string }>
  const foundIds = new Set(results.map((row) => row.id))
  const missing = relatedTerms.filter((id) => !foundIds.has(id))
  if (missing.length > 0) {
    throw validationError(`related_terms contains unknown ids: ${missing.join(', ')}`)
  }

  const crossDomain = results.find((row) => row.domain !== domain)
  if (crossDomain) {
    throw validationError('related_terms must reference terms in the same domain')
  }
}

catalogRouter.get('/datasets', validate(DatasetQuerySchema, 'query'), async (c) => {
  const query = c.req.valid('query')
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20
  const offset = (page - 1) * pageSize

  const whereClause = query.domain ? 'WHERE domain = ?' : ''
  const bindings = query.domain ? [query.domain] : []

  const countResult = (await c.env.DB.prepare(
    `SELECT COUNT(*) as total FROM catalog_datasets ${whereClause}`,
  )
    .bind(...bindings)
    .first()) as { total: number } | null

  const total = countResult?.total ?? 0
  const totalPages = Math.ceil(total / pageSize)

  const rows = await c.env.DB.prepare(
    `SELECT id, domain, name, description, schema_json, lineage_json, owner, tags, created_at, updated_at
       FROM catalog_datasets ${whereClause} ORDER BY updated_at DESC LIMIT ? OFFSET ?`,
  )
    .bind(...bindings, pageSize, offset)
    .all()

  const response: PaginatedResponse<CatalogDataset> = {
    success: true,
    data: rows.results as CatalogDataset[],
    pagination: {
      page,
      pageSize,
      total,
      totalPages,
    },
  }

  return c.json(response)
})

catalogRouter.get('/datasets/:id', validate(IdParamSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const dataset = await c.env.DB.prepare(
    'SELECT id, domain, name, description, schema_json, lineage_json, owner, tags, created_at, updated_at FROM catalog_datasets WHERE id = ?',
  )
    .bind(id)
    .first()

  if (!dataset) {
    throw notFound('Catalog dataset not found')
  }

  const response: ApiSuccess<CatalogDataset> = {
    success: true,
    data: dataset as CatalogDataset,
  }

  return c.json(response)
})

catalogRouter.get(
  '/datasets/:id/preview',
  validate(IdParamSchema, 'param'),
  validate(PreviewQuerySchema, 'query'),
  async (c) => {
    const { id } = c.req.valid('param')
    const query = c.req.valid('query')
    const limit = query.limit ?? 20

    const dataset = await c.env.DB.prepare('SELECT id FROM catalog_datasets WHERE id = ?')
      .bind(id)
      .first()
    if (!dataset) {
      throw notFound('Catalog dataset not found')
    }

    const source = PREVIEW_SOURCE_BY_DATASET_ID[id]
    if (!source) {
      const response: ApiSuccess<DatasetPreviewResponse> = {
        success: true,
        data: {
          datasetId: id,
          source: {
            kind: 'unmapped',
            table: null,
          },
          columns: [],
          rows: [],
          meta: {
            limit,
            returned: 0,
            reason: 'dataset-not-mapped',
          },
        },
      }

      return c.json(response)
    }

    const statement = `SELECT * FROM ${source.table} ORDER BY ${source.sortCol} DESC LIMIT ?`
    const previewRows = await c.env.DB.prepare(statement).bind(limit).all()
    const rows = previewRows.results as Array<Record<string, unknown>>
    const columns = Object.keys(rows[0] ?? {})
    const reason = rows.length === 0 ? 'empty-source' : undefined

    const response: ApiSuccess<DatasetPreviewResponse> = {
      success: true,
      data: {
        datasetId: id,
        source: {
          kind: 'mapped-table',
          table: source.table,
        },
        columns,
        rows,
        meta: {
          limit,
          returned: rows.length,
          reason,
        },
      },
    }

    return c.json(response)
  },
)

catalogRouter.get('/datasets/:id/columns', validate(IdParamSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const dataset = await c.env.DB.prepare('SELECT id FROM catalog_datasets WHERE id = ?')
    .bind(id)
    .first()

  if (!dataset) {
    throw notFound('Catalog dataset not found')
  }

  const rows = await c.env.DB.prepare(
    'SELECT dataset_id, column_name, data_type, description, is_pii, examples FROM catalog_columns WHERE dataset_id = ? ORDER BY column_name',
  )
    .bind(id)
    .all()

  const columns = rows.results.map(
    (col: Record<string, unknown>): CatalogColumn => ({
      dataset_id: String(col.dataset_id),
      column_name: String(col.column_name),
      data_type: String(col.data_type),
      description: typeof col.description === 'string' ? col.description : null,
      is_pii: Boolean(col.is_pii),
      examples: typeof col.examples === 'string' ? col.examples : null,
    }),
  )

  const response: ApiSuccess<CatalogColumn[]> = {
    success: true,
    data: columns,
  }

  return c.json(response)
})

catalogRouter.get('/lineage/:datasetId', validate(LineageParamSchema, 'param'), async (c) => {
  const { datasetId } = c.req.valid('param')

  const dataset = (await c.env.DB.prepare(
    'SELECT id, domain, name, lineage_json FROM catalog_datasets WHERE id = ?',
  )
    .bind(datasetId)
    .first()) as {
    id: string
    domain: string
    name: string
    lineage_json: string | null
  } | null

  if (!dataset) {
    throw notFound('Catalog dataset not found')
  }

  const rawLineage = parseLineageJson(dataset.lineage_json)
  const normalized =
    rawLineage === null
      ? buildDefaultSelfNodeGraph(dataset)
      : normalizeLegacyLineageToGraph(rawLineage, dataset)

  if (!normalized) {
    throw validationError('lineage_json has unsupported shape')
  }

  assertLineageGraphIntegrity(normalized)

  const response: ApiSuccess<LineageGraph> = {
    success: true,
    data: normalized,
  }

  return c.json(response)
})

catalogRouter.put(
  '/lineage/:datasetId',
  validate(LineageParamSchema, 'param'),
  validateBody(LineageGraphSchema),
  async (c) => {
    const { datasetId } = c.req.valid('param')
    const graph = c.req.valid('json')

    const dataset = await c.env.DB.prepare('SELECT id FROM catalog_datasets WHERE id = ?')
      .bind(datasetId)
      .first()

    if (!dataset) {
      throw notFound('Catalog dataset not found')
    }

    assertLineageGraphIntegrity(graph)

    const payload: LineageGraph = {
      version: 1,
      nodes: graph.nodes,
      edges: graph.edges,
    }

    await c.env.DB.prepare(
      'UPDATE catalog_datasets SET lineage_json = ?, updated_at = ? WHERE id = ?',
    )
      .bind(JSON.stringify(payload), nowIso(), datasetId)
      .run()

    const response: ApiSuccess<LineageGraph> = {
      success: true,
      data: payload,
    }

    return c.json(response)
  },
)

catalogRouter.get('/glossary', validate(GlossaryQuerySchema, 'query'), async (c) => {
  const query = c.req.valid('query')
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20
  const offset = (page - 1) * pageSize

  const conditions: string[] = []
  const bindings: (string | number)[] = []

  if (query.domain) {
    conditions.push('domain = ?')
    bindings.push(query.domain)
  }

  if (query.q) {
    conditions.push('(term LIKE ? OR definition LIKE ?)')
    const pattern = `%${query.q}%`
    bindings.push(pattern, pattern)
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : ''

  const countResult = (await c.env.DB.prepare(
    `SELECT COUNT(*) as total FROM glossary_terms ${whereClause}`,
  )
    .bind(...bindings)
    .first()) as { total: number } | null

  const rows = await c.env.DB.prepare(
    `SELECT id, domain, term, definition, related_terms, created_at, updated_at
       FROM glossary_terms ${whereClause} ORDER BY updated_at DESC LIMIT ? OFFSET ?`,
  )
    .bind(...bindings, pageSize, offset)
    .all()

  const terms = rows.results.map((row: unknown) => mapGlossaryRow(row as Record<string, unknown>))
  const total = countResult?.total ?? 0

  const response: PaginatedResponse<GlossaryTerm> = {
    success: true,
    data: terms,
    pagination: {
      page,
      pageSize,
      total,
      totalPages: Math.ceil(total / pageSize),
    },
  }

  return c.json(response)
})

catalogRouter.get('/glossary/:id', validate(GlossaryIdParamSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const row = await c.env.DB.prepare(
    'SELECT id, domain, term, definition, related_terms, created_at, updated_at FROM glossary_terms WHERE id = ?',
  )
    .bind(id)
    .first()

  if (!row) {
    throw notFound('Glossary term not found')
  }

  const response: ApiSuccess<GlossaryTerm> = {
    success: true,
    data: mapGlossaryRow(row as Record<string, unknown>),
  }

  return c.json(response)
})

catalogRouter.post('/glossary', validateBody(GlossaryCreateBodySchema), async (c) => {
  const body = c.req.valid('json')
  const id = generateUuidV7()
  const createdAt = nowIso()
  const relatedTerms = body.related_terms ?? []

  await assertRelatedTermsIntegrity(c, {
    domain: body.domain,
    targetId: id,
    relatedTerms,
  })

  try {
    await c.env.DB.prepare(
      'INSERT INTO glossary_terms (id, domain, term, definition, related_terms, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
    )
      .bind(
        id,
        body.domain,
        body.term,
        body.definition,
        JSON.stringify(relatedTerms),
        createdAt,
        createdAt,
      )
      .run()
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes('UNIQUE constraint failed: glossary_terms.domain, glossary_terms.term')) {
      throw new AppError(
        409,
        'Conflict',
        '/errors/conflict',
        'Glossary term already exists in this domain',
      )
    }
    throw error
  }

  const created = await c.env.DB.prepare(
    'SELECT id, domain, term, definition, related_terms, created_at, updated_at FROM glossary_terms WHERE id = ?',
  )
    .bind(id)
    .first()

  const response: ApiSuccess<GlossaryTerm> = {
    success: true,
    data: mapGlossaryRow(created as Record<string, unknown>),
  }

  return c.json(response, 201)
})

catalogRouter.put(
  '/glossary/:id',
  validate(GlossaryIdParamSchema, 'param'),
  validateBody(GlossaryUpdateBodySchema),
  async (c) => {
    const { id } = c.req.valid('param')
    const body = c.req.valid('json')

    const existing = (await c.env.DB.prepare(
      'SELECT id, domain, term, definition, related_terms, created_at, updated_at FROM glossary_terms WHERE id = ?',
    )
      .bind(id)
      .first()) as Record<string, unknown> | null

    if (!existing) {
      throw notFound('Glossary term not found')
    }

    const nextDomain = String(existing.domain)
    const nextTerm = body.term ?? String(existing.term)
    const nextDefinition = body.definition ?? String(existing.definition)
    const nextRelatedTerms = body.related_terms ?? parseRelatedTerms(existing.related_terms)

    await assertRelatedTermsIntegrity(c, {
      domain: nextDomain,
      targetId: id,
      relatedTerms: nextRelatedTerms,
    })

    try {
      await c.env.DB.prepare(
        'UPDATE glossary_terms SET term = ?, definition = ?, related_terms = ?, updated_at = ? WHERE id = ?',
      )
        .bind(nextTerm, nextDefinition, JSON.stringify(nextRelatedTerms), nowIso(), id)
        .run()
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      if (
        message.includes('UNIQUE constraint failed: glossary_terms.domain, glossary_terms.term')
      ) {
        throw new AppError(
          409,
          'Conflict',
          '/errors/conflict',
          'Glossary term already exists in this domain',
        )
      }
      throw error
    }

    const updated = await c.env.DB.prepare(
      'SELECT id, domain, term, definition, related_terms, created_at, updated_at FROM glossary_terms WHERE id = ?',
    )
      .bind(id)
      .first()

    const response: ApiSuccess<GlossaryTerm> = {
      success: true,
      data: mapGlossaryRow(updated as Record<string, unknown>),
    }

    return c.json(response)
  },
)

catalogRouter.delete('/glossary/:id', validate(GlossaryIdParamSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const existing = await c.env.DB.prepare('SELECT id FROM glossary_terms WHERE id = ?')
    .bind(id)
    .first()

  if (!existing) {
    throw notFound('Glossary term not found')
  }

  await c.env.DB.batch([
    c.env.DB.prepare('DELETE FROM glossary_terms WHERE id = ?').bind(id),
    c.env.DB.prepare(
      `UPDATE glossary_terms
       SET related_terms = COALESCE(
         (SELECT json_group_array(value)
          FROM json_each(glossary_terms.related_terms)
          WHERE value <> ?),
         '[]'
       ),
       updated_at = ?
       WHERE EXISTS (
         SELECT 1
         FROM json_each(glossary_terms.related_terms)
         WHERE value = ?
       )`,
    ).bind(id, nowIso(), id),
  ])

  const response: ApiSuccess<{ id: string; deleted: true }> = {
    success: true,
    data: {
      id,
      deleted: true,
    },
  }

  return c.json(response)
})

export default catalogRouter
