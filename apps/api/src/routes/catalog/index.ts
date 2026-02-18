import { zValidator } from '@hono/zod-validator'
import { Hono } from 'hono'
import { z } from 'zod'
import type { ApiSuccess, Env, PaginatedResponse } from '@pseudolab/shared-types'
import { notFound, validationError } from '../../lib/errors'

const catalogRouter = new Hono<{ Bindings: Env }>()

const DatasetQuerySchema = z.object({
  domain: z.string().optional(),
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
})

const IdParamSchema = z.object({
  id: z.string().min(1),
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

catalogRouter.get('/datasets', validate(DatasetQuerySchema, 'query'), async (c) => {
  const query = c.req.valid('query')
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20
  const offset = (page - 1) * pageSize

  const whereClause = query.domain ? 'WHERE domain = ?' : ''
  const bindings = query.domain ? [query.domain] : []

  const countResult = (await c.env.DB
    .prepare(`SELECT COUNT(*) as total FROM catalog_datasets ${whereClause}`)
    .bind(...bindings)
    .first()) as { total: number } | null

  const total = countResult?.total ?? 0
  const totalPages = Math.ceil(total / pageSize)

  const rows = await c.env.DB
    .prepare(
      `SELECT * FROM catalog_datasets ${whereClause} ORDER BY updated_at DESC LIMIT ? OFFSET ?`
    )
    .bind(...bindings, pageSize, offset)
    .all()

  const response: PaginatedResponse<unknown> = {
    success: true,
    data: rows.results,
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

  const dataset = await c.env.DB
    .prepare('SELECT * FROM catalog_datasets WHERE id = ?')
    .bind(id)
    .first()

  if (!dataset) {
    throw notFound('Catalog dataset not found')
  }

  const response: ApiSuccess<unknown> = {
    success: true,
    data: dataset,
  }

  return c.json(response)
})

catalogRouter.get('/datasets/:id/columns', validate(IdParamSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const dataset = await c.env.DB
    .prepare('SELECT id FROM catalog_datasets WHERE id = ?')
    .bind(id)
    .first()

  if (!dataset) {
    throw notFound('Catalog dataset not found')
  }

  const rows = await c.env.DB
    .prepare('SELECT * FROM catalog_columns WHERE dataset_id = ? ORDER BY column_name')
    .bind(id)
    .all()

  const columns = rows.results.map((col: Record<string, unknown>) => ({
    ...col,
    is_pii: Boolean(col.is_pii),
  }))

  const response: ApiSuccess<unknown> = {
    success: true,
    data: columns,
  }

  return c.json(response)
})

export default catalogRouter
