import { zValidator } from '@hono/zod-validator'
import type { DatasetComment } from '@pseudolab/shared-types'
import { parseJsonTextArray } from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { z } from 'zod'
import { forbidden, notFound, validationError } from '../../lib/errors'
import { nanoid } from '../../lib/id'
import type { AuthEnv } from '../../middleware/user-auth'
import { requireUserAuth } from '../../middleware/user-auth'

// --- Validation ---

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

const CommentCategoryEnum = z.enum(['limitation', 'purpose', 'usage'])
const CommentSourceEnum = z.enum(['human', 'ai-auto', 'ai-assisted'])

const DatasetIdSchema = z.object({
  id: z.string().min(1),
})

const CommentIdSchema = z.object({
  id: z.string().min(1),
  commentId: z.string().min(1),
})

const ListCommentsQuerySchema = z.object({
  category: CommentCategoryEnum.optional(),
  source: CommentSourceEnum.optional(),
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
})

const CreateCommentSchema = z.object({
  category: CommentCategoryEnum,
  content: z.string().trim().min(1).max(5000),
  source: CommentSourceEnum.default('human'),
  source_query_ids: z.array(z.string()).max(50).optional(),
})

const UpdateCommentSchema = z.object({
  content: z.string().trim().min(1).max(5000),
})

// --- Helpers ---

type CommentRow = {
  id: string
  dataset_id: string
  user_email: string
  user_name: string | null
  category: string
  content: string
  source: string
  source_query_ids: string | null
  created_at: string
  updated_at: string | null
}

function mapCommentRow(row: CommentRow): DatasetComment {
  return {
    id: row.id,
    dataset_id: row.dataset_id,
    user_email: row.user_email,
    user_name: row.user_name,
    category: row.category as DatasetComment['category'],
    content: row.content,
    source: row.source as DatasetComment['source'],
    source_query_ids: parseJsonTextArray(row.source_query_ids),
    created_at: row.created_at,
    updated_at: row.updated_at,
  }
}

function nowIso(): string {
  return new Date().toISOString()
}

// --- Router ---

const commentsRouter = new Hono<AuthEnv>()
commentsRouter.use('*', requireUserAuth)

// GET /api/datasets/:id/comments
commentsRouter.get(
  '/:id/comments',
  validate(DatasetIdSchema, 'param'),
  validate(ListCommentsQuerySchema, 'query'),
  async (c) => {
    const { id: datasetId } = c.req.valid('param')
    const query = c.req.valid('query')
    const page = query.page ?? 1
    const pageSize = query.pageSize ?? 20
    const offset = (page - 1) * pageSize

    const conditions: string[] = ['dataset_id = ?']
    const bindings: unknown[] = [datasetId]

    if (query.category) {
      conditions.push('category = ?')
      bindings.push(query.category)
    }
    if (query.source) {
      conditions.push('source = ?')
      bindings.push(query.source)
    }

    const whereClause = `WHERE ${conditions.join(' AND ')}`

    const countResult = (await c.env.DB.prepare(
      `SELECT COUNT(*) as total FROM dataset_comments ${whereClause}`,
    )
      .bind(...bindings)
      .first()) as { total: number } | null

    const total = countResult?.total ?? 0
    const totalPages = Math.ceil(total / pageSize)

    const rows = await c.env.DB.prepare(
      `SELECT id, dataset_id, user_email, user_name, category, content, source, source_query_ids, created_at, updated_at
       FROM dataset_comments ${whereClause}
       ORDER BY created_at DESC LIMIT ? OFFSET ?`,
    )
      .bind(...bindings, pageSize, offset)
      .all<CommentRow>()

    return c.json({
      success: true,
      data: rows.results.map(mapCommentRow),
      pagination: { page, pageSize, total, totalPages },
    })
  },
)

// POST /api/datasets/:id/comments
commentsRouter.post(
  '/:id/comments',
  validate(DatasetIdSchema, 'param'),
  validateBody(CreateCommentSchema),
  async (c) => {
    const { id: datasetId } = c.req.valid('param')
    const body = c.req.valid('json')
    const user = c.get('user')

    // Verify dataset exists
    const dataset = await c.env.DB.prepare('SELECT id FROM catalog_datasets WHERE id = ?')
      .bind(datasetId)
      .first()

    if (!dataset) {
      throw notFound('Dataset not found')
    }

    const commentId = nanoid()
    const now = nowIso()
    const sourceQueryIds = body.source_query_ids ? JSON.stringify(body.source_query_ids) : null

    await c.env.DB.prepare(
      `INSERT INTO dataset_comments (id, dataset_id, user_email, user_name, category, content, source, source_query_ids, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    )
      .bind(
        commentId,
        datasetId,
        user.email,
        user.name || null,
        body.category,
        body.content,
        body.source,
        sourceQueryIds,
        now,
      )
      .run()

    const created: DatasetComment = {
      id: commentId,
      dataset_id: datasetId,
      user_email: user.email,
      user_name: user.name || null,
      category: body.category,
      content: body.content,
      source: body.source,
      source_query_ids: body.source_query_ids ?? [],
      created_at: now,
      updated_at: null,
    }

    return c.json({ success: true, data: created }, 201)
  },
)

// PUT /api/datasets/:id/comments/:commentId
commentsRouter.put(
  '/:id/comments/:commentId',
  validate(CommentIdSchema, 'param'),
  validateBody(UpdateCommentSchema),
  async (c) => {
    const { commentId } = c.req.valid('param')
    const body = c.req.valid('json')
    const user = c.get('user')

    const existing = await c.env.DB.prepare(
      'SELECT id, user_email, source FROM dataset_comments WHERE id = ?',
    )
      .bind(commentId)
      .first<{ id: string; user_email: string; source: string }>()

    if (!existing) {
      throw notFound('Comment not found')
    }

    // Authorization: own comment or AI-generated
    if (existing.user_email !== user.email && existing.source === 'human') {
      throw forbidden('You can only edit your own comments')
    }

    const now = nowIso()
    await c.env.DB.prepare('UPDATE dataset_comments SET content = ?, updated_at = ? WHERE id = ?')
      .bind(body.content, now, commentId)
      .run()

    const updated = await c.env.DB.prepare(
      `SELECT id, dataset_id, user_email, user_name, category, content, source, source_query_ids, created_at, updated_at
       FROM dataset_comments WHERE id = ?`,
    )
      .bind(commentId)
      .first<CommentRow>()

    if (!updated) {
      throw notFound('Comment not found after update')
    }
    return c.json({ success: true, data: mapCommentRow(updated) })
  },
)

// DELETE /api/datasets/:id/comments/:commentId
commentsRouter.delete('/:id/comments/:commentId', validate(CommentIdSchema, 'param'), async (c) => {
  const { commentId } = c.req.valid('param')
  const user = c.get('user')

  const existing = await c.env.DB.prepare(
    'SELECT id, user_email FROM dataset_comments WHERE id = ?',
  )
    .bind(commentId)
    .first<{ id: string; user_email: string }>()

  if (!existing) {
    throw notFound('Comment not found')
  }

  if (existing.user_email !== user.email) {
    throw forbidden('You can only delete your own comments')
  }

  await c.env.DB.prepare('DELETE FROM dataset_comments WHERE id = ?').bind(commentId).run()

  return c.json({ success: true, data: { deleted: true } })
})

export default commentsRouter
