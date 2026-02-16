import { zValidator } from '@hono/zod-validator'
import { Hono } from 'hono'
import { z } from 'zod'
import type { ApiSuccess, Env, PaginatedResponse } from '@pseudolab/shared-types'
import { notFound, validationError } from '../../lib/errors'

const githubRouter = new Hono<{ Bindings: Env }>()

const EventsQuerySchema = z.object({
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
  type: z.string().optional(),
  repo: z.string().optional(),
  org: z.string().optional(),
})

const DailyStatsQuerySchema = z.object({
  startDate: z.string().optional(),
  endDate: z.string().optional(),
  org: z.string().optional(),
  repo: z.string().optional(),
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

githubRouter.get('/events', validate(EventsQuerySchema, 'query'), (c) => {
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

githubRouter.get('/events/:id', validate(IdParamSchema, 'param'), () => {
  throw notFound('GitHub event not found')
})

githubRouter.get('/stats/daily', validate(DailyStatsQuerySchema, 'query'), (c) => {
  const response: ApiSuccess<unknown[]> = {
    success: true,
    data: [],
  }

  return c.json(response)
})

export default githubRouter
