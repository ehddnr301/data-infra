import { zValidator } from '@hono/zod-validator'
import type { ApiSuccess, Env, PaginatedResponse } from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { z } from 'zod'
import { notFound, validationError } from '../../lib/errors'

const discordRouter = new Hono<{ Bindings: Env }>()

// ── 스키마 정의 ──

const MessagesQuerySchema = z.object({
  channel: z.string().optional(),
  author: z.string().optional(),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
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

// ── GET /api/discord/messages ──

discordRouter.get('/messages', validate(MessagesQuerySchema, 'query'), async (c) => {
  const query = c.req.valid('query')
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20
  const offset = (page - 1) * pageSize

  // WHERE 절 동적 구성
  const conditions: string[] = []
  const bindings: (string | number)[] = []

  if (query.channel) {
    conditions.push('channel_id = ?')
    bindings.push(query.channel)
  }
  if (query.author) {
    conditions.push('author_id = ?')
    bindings.push(query.author)
  }
  if (query.startDate) {
    conditions.push('created_at >= ?')
    bindings.push(query.startDate)
  }
  if (query.endDate) {
    conditions.push('created_at <= ?')
    bindings.push(query.endDate)
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : ''

  const countResult = (await c.env.DB.prepare(
    `SELECT COUNT(*) as total FROM discord_messages ${whereClause}`,
  )
    .bind(...bindings)
    .first()) as { total: number } | null

  const total = countResult?.total ?? 0
  const totalPages = Math.ceil(total / pageSize)

  const rows = await c.env.DB.prepare(
    `SELECT * FROM discord_messages ${whereClause} ORDER BY created_at DESC LIMIT ? OFFSET ?`,
  )
    .bind(...bindings, pageSize, offset)
    .all()

  const response: PaginatedResponse<unknown> = {
    success: true,
    data: rows.results,
    pagination: { page, pageSize, total, totalPages },
  }

  return c.json(response)
})

// ── GET /api/discord/messages/:id ──

discordRouter.get('/messages/:id', validate(IdParamSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const message = await c.env.DB.prepare('SELECT * FROM discord_messages WHERE id = ?')
    .bind(id)
    .first()

  if (!message) {
    throw notFound('Discord message not found')
  }

  const response: ApiSuccess<unknown> = {
    success: true,
    data: message,
  }

  return c.json(response)
})

// ── GET /api/discord/channels ──

discordRouter.get('/channels', async (c) => {
  const rows = await c.env.DB.prepare(
    `SELECT
        w.channel_id,
        w.channel_name,
        w.last_message_id,
        w.scan_cursor,
        w.last_collected_at,
        w.total_collected,
        (SELECT COUNT(*) FROM discord_messages m WHERE m.channel_id = w.channel_id) as message_count,
        (SELECT MAX(created_at) FROM discord_messages m WHERE m.channel_id = w.channel_id) as latest_message_at
      FROM discord_watermarks w
      ORDER BY w.channel_name`,
  ).all()

  const channels = rows.results.map((row: Record<string, unknown>) => ({
    ...row,
    is_collecting: row.scan_cursor !== null,
  }))

  const response: ApiSuccess<unknown> = {
    success: true,
    data: channels,
  }

  return c.json(response)
})

export default discordRouter
