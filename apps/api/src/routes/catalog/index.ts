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

catalogRouter.get('/datasets', validate(DatasetQuerySchema, 'query'), (c) => {
  const query = c.req.valid('query')
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20

  const response: PaginatedResponse<unknown> = {
    success: true,
    data: [],
    pagination: {
      page,
      pageSize,
      total: 0,
      totalPages: 0,
    },
  }

  return c.json(response)
})

catalogRouter.get('/datasets/:id', validate(IdParamSchema, 'param'), () => {
  throw notFound('Catalog dataset not found')
})

catalogRouter.get('/datasets/:id/columns', validate(IdParamSchema, 'param'), () => {
  throw notFound('Catalog dataset columns not found')
})

export default catalogRouter
