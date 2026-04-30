import { zValidator } from '@hono/zod-validator'
import type {
  DiscussionComment,
  DiscussionLinkedRefs,
  DiscussionPost,
  DiscussionPostSummary,
  DiscussionUpvoteResponse,
  DomainName,
} from '@pseudolab/shared-types'
import type { Context } from 'hono'
import { Hono } from 'hono'
import { z } from 'zod'
import { badRequest, notFound, validationError } from '../../lib/errors'
import { nanoid } from '../../lib/id'
import type { AuthEnv } from '../../middleware/user-auth'
import { requireUserAuth } from '../../middleware/user-auth'

// --- Validation helpers ---

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

const SourceEnum = z.enum(['human', 'ai-auto', 'ai-assisted'])

const PostIdSchema = z.object({ id: z.string().min(1) })
const PostCommentIdSchema = z.object({
  id: z.string().min(1),
  commentId: z.string().min(1),
})

const ListPostsQuerySchema = z.object({
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
  sort: z.enum(['popular', 'latest']).optional(),
  dataset_id: z.string().min(1).optional(),
  listing_id: z.string().min(1).optional(),
  query_history_id: z.string().min(1).optional(),
})

const optionalNonEmpty = z
  .union([z.string().trim().min(1), z.null()])
  .optional()
  .transform((v) => (v == null ? undefined : v))

const CreatePostSchema = z.object({
  title: z.string().trim().min(1).max(120),
  content: z.string().trim().min(1).max(4000),
  source: SourceEnum.default('ai-assisted'),
  dataset_id: optionalNonEmpty,
  listing_id: optionalNonEmpty,
  query_history_id: optionalNonEmpty,
})

const CreateCommentSchema = z.object({
  content: z.string().trim().min(1).max(2000),
  source: SourceEnum.default('ai-assisted'),
  parent_comment_id: optionalNonEmpty,
})

// --- Types ---

type DiscussionPostRow = {
  id: string
  title: string
  content: string
  user_email: string
  user_name: string | null
  source: string
  dataset_id: string | null
  listing_id: string | null
  query_history_id: string | null
  upvote_count: number
  comment_count: number
  created_at: string
  dataset_name: string | null
  listing_domain: string | null
  listing_slug: string | null
  listing_title: string | null
  query_status: string | null
}

type DiscussionCommentRow = {
  id: string
  post_id: string
  parent_comment_id: string | null
  user_email: string
  user_name: string | null
  source: string
  content: string
  upvote_count: number
  created_at: string
}

const POST_SELECT = `SELECT
    p.id, p.title, p.content, p.user_email, p.user_name, p.source,
    p.dataset_id, p.listing_id, p.query_history_id,
    p.upvote_count, p.comment_count, p.created_at,
    d.name AS dataset_name,
    l.domain AS listing_domain, l.slug AS listing_slug, l.title AS listing_title,
    q.status AS query_status
  FROM discussion_posts p
  LEFT JOIN catalog_datasets d ON d.id = p.dataset_id
  LEFT JOIN marketplace_listings l ON l.id = p.listing_id
  LEFT JOIN query_history q ON q.id = p.query_history_id`

function buildLinked(row: DiscussionPostRow): DiscussionLinkedRefs {
  return {
    dataset:
      row.dataset_id && row.dataset_name
        ? { id: row.dataset_id, name: row.dataset_name }
        : row.dataset_id
          ? { id: row.dataset_id, name: row.dataset_id }
          : null,
    listing:
      row.listing_id && row.listing_domain && row.listing_slug && row.listing_title
        ? {
            id: row.listing_id,
            domain: row.listing_domain as DomainName,
            slug: row.listing_slug,
            title: row.listing_title,
          }
        : null,
    query_history:
      row.query_history_id && row.query_status
        ? {
            id: row.query_history_id,
            status: row.query_status as 'success' | 'error',
          }
        : null,
  }
}

const EXCERPT_MAX = 200

function buildExcerpt(content: string): string {
  const collapsed = content.replace(/\s+/g, ' ').trim()
  return collapsed.length > EXCERPT_MAX ? `${collapsed.slice(0, EXCERPT_MAX)}…` : collapsed
}

function mapSummary(row: DiscussionPostRow): DiscussionPostSummary {
  return {
    id: row.id,
    title: row.title,
    excerpt: buildExcerpt(row.content),
    user_email: row.user_email,
    user_name: row.user_name,
    source: row.source as DiscussionPostSummary['source'],
    dataset_id: row.dataset_id,
    listing_id: row.listing_id,
    query_history_id: row.query_history_id,
    upvote_count: row.upvote_count,
    comment_count: row.comment_count,
    created_at: row.created_at,
    linked: buildLinked(row),
  }
}

function mapPost(row: DiscussionPostRow): DiscussionPost {
  return {
    id: row.id,
    title: row.title,
    content: row.content,
    user_email: row.user_email,
    user_name: row.user_name,
    source: row.source as DiscussionPost['source'],
    dataset_id: row.dataset_id,
    listing_id: row.listing_id,
    query_history_id: row.query_history_id,
    upvote_count: row.upvote_count,
    comment_count: row.comment_count,
    created_at: row.created_at,
    linked: buildLinked(row),
  }
}

function mapComment(row: DiscussionCommentRow): DiscussionComment {
  return {
    id: row.id,
    post_id: row.post_id,
    parent_comment_id: row.parent_comment_id,
    user_email: row.user_email,
    user_name: row.user_name,
    source: row.source as DiscussionComment['source'],
    content: row.content,
    upvote_count: row.upvote_count,
    created_at: row.created_at,
  }
}

function nowIso(): string {
  return new Date().toISOString()
}

// --- Router ---

const discussionsRouter = new Hono<AuthEnv>()

// GET /api/discussions — public list
discussionsRouter.get('/', validate(ListPostsQuerySchema, 'query'), async (c) => {
  const query = c.req.valid('query')
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20
  const offset = (page - 1) * pageSize
  const sort = query.sort ?? 'popular'

  const conditions: string[] = []
  const bindings: unknown[] = []
  if (query.dataset_id) {
    conditions.push('p.dataset_id = ?')
    bindings.push(query.dataset_id)
  }
  if (query.listing_id) {
    conditions.push('p.listing_id = ?')
    bindings.push(query.listing_id)
  }
  if (query.query_history_id) {
    conditions.push('p.query_history_id = ?')
    bindings.push(query.query_history_id)
  }
  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : ''
  const orderBy =
    sort === 'latest'
      ? 'ORDER BY p.created_at DESC'
      : 'ORDER BY p.upvote_count DESC, p.created_at DESC'

  const countResult = (await c.env.DB.prepare(
    `SELECT COUNT(*) as total FROM discussion_posts p ${whereClause}`,
  )
    .bind(...bindings)
    .first()) as { total: number } | null

  const total = countResult?.total ?? 0
  const totalPages = total === 0 ? 0 : Math.ceil(total / pageSize)

  const rows = await c.env.DB.prepare(`${POST_SELECT} ${whereClause} ${orderBy} LIMIT ? OFFSET ?`)
    .bind(...bindings, pageSize, offset)
    .all<DiscussionPostRow>()

  return c.json({
    success: true,
    data: rows.results.map(mapSummary),
    pagination: { page, pageSize, total, totalPages },
  })
})

// GET /api/discussions/:id — public detail
discussionsRouter.get('/:id', validate(PostIdSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const row = await c.env.DB.prepare(`${POST_SELECT} WHERE p.id = ?`)
    .bind(id)
    .first<DiscussionPostRow>()

  if (!row) {
    throw notFound('Discussion post not found')
  }

  return c.json({ success: true, data: mapPost(row) })
})

// GET /api/discussions/:id/comments — public flat list
discussionsRouter.get('/:id/comments', validate(PostIdSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const post = await c.env.DB.prepare('SELECT id FROM discussion_posts WHERE id = ?')
    .bind(id)
    .first<{ id: string }>()
  if (!post) {
    throw notFound('Discussion post not found')
  }

  const rows = await c.env.DB.prepare(
    `SELECT id, post_id, parent_comment_id, user_email, user_name, source, content, upvote_count, created_at
     FROM discussion_comments
     WHERE post_id = ?
     ORDER BY created_at ASC, id ASC`,
  )
    .bind(id)
    .all<DiscussionCommentRow>()

  return c.json({ success: true, data: rows.results.map(mapComment) })
})

// --- Authenticated writes ---

discussionsRouter.post('/', requireUserAuth, validateBody(CreatePostSchema), async (c) => {
  const body = c.req.valid('json')
  const user = c.get('user')

  const datasetId = body.dataset_id ?? null
  const listingId = body.listing_id ?? null
  const queryHistoryId = body.query_history_id ?? null

  if (!datasetId && !listingId && !queryHistoryId) {
    throw badRequest('At least one of dataset_id, listing_id, or query_history_id must be provided')
  }

  if (datasetId) {
    const found = await c.env.DB.prepare('SELECT id FROM catalog_datasets WHERE id = ?')
      .bind(datasetId)
      .first()
    if (!found) {
      throw notFound(`dataset_id not found: ${datasetId}`)
    }
  }
  if (listingId) {
    const found = await c.env.DB.prepare('SELECT id FROM marketplace_listings WHERE id = ?')
      .bind(listingId)
      .first()
    if (!found) {
      throw notFound(`listing_id not found: ${listingId}`)
    }
  }
  if (queryHistoryId) {
    const found = await c.env.DB.prepare('SELECT id FROM query_history WHERE id = ?')
      .bind(queryHistoryId)
      .first()
    if (!found) {
      throw notFound(`query_history_id not found: ${queryHistoryId}`)
    }
  }

  const postId = nanoid()
  const now = nowIso()

  await c.env.DB.prepare(
    `INSERT INTO discussion_posts
       (id, title, content, user_email, user_name, source, dataset_id, listing_id, query_history_id, upvote_count, comment_count, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)`,
  )
    .bind(
      postId,
      body.title,
      body.content,
      user.email,
      user.name || null,
      body.source,
      datasetId,
      listingId,
      queryHistoryId,
      now,
    )
    .run()

  const row = await c.env.DB.prepare(`${POST_SELECT} WHERE p.id = ?`)
    .bind(postId)
    .first<DiscussionPostRow>()
  if (!row) {
    throw notFound('Discussion post not found after insert')
  }

  return c.json({ success: true, data: mapPost(row) }, 201)
})

discussionsRouter.post(
  '/:id/comments',
  requireUserAuth,
  validate(PostIdSchema, 'param'),
  validateBody(CreateCommentSchema),
  async (c) => {
    const { id: postId } = c.req.valid('param')
    const body = c.req.valid('json')
    const user = c.get('user')

    const post = await c.env.DB.prepare('SELECT id FROM discussion_posts WHERE id = ?')
      .bind(postId)
      .first<{ id: string }>()
    if (!post) {
      throw notFound('Discussion post not found')
    }

    const parentId = body.parent_comment_id ?? null
    if (parentId) {
      const parent = await c.env.DB.prepare('SELECT post_id FROM discussion_comments WHERE id = ?')
        .bind(parentId)
        .first<{ post_id: string }>()
      if (!parent) {
        throw badRequest(`parent_comment_id not found: ${parentId}`)
      }
      if (parent.post_id !== postId) {
        throw badRequest('parent_comment_id belongs to a different post')
      }
    }

    const commentId = nanoid()
    const now = nowIso()

    await c.env.DB.prepare(
      `INSERT INTO discussion_comments
         (id, post_id, parent_comment_id, user_email, user_name, source, content, upvote_count, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)`,
    )
      .bind(
        commentId,
        postId,
        parentId,
        user.email,
        user.name || null,
        body.source,
        body.content,
        now,
      )
      .run()

    await c.env.DB.prepare(
      'UPDATE discussion_posts SET comment_count = comment_count + 1 WHERE id = ?',
    )
      .bind(postId)
      .run()

    const created: DiscussionComment = {
      id: commentId,
      post_id: postId,
      parent_comment_id: parentId,
      user_email: user.email,
      user_name: user.name || null,
      source: body.source,
      content: body.content,
      upvote_count: 0,
      created_at: now,
    }

    return c.json({ success: true, data: created }, 201)
  },
)

async function applyUpvote(
  c: Context<AuthEnv>,
  targetType: 'post' | 'comment',
  targetId: string,
  countTable: 'discussion_posts' | 'discussion_comments',
): Promise<DiscussionUpvoteResponse> {
  const user = c.get('user')
  const voteId = nanoid()
  const now = nowIso()

  const insertResult = await c.env.DB.prepare(
    `INSERT OR IGNORE INTO discussion_votes
       (id, target_type, target_id, user_email, user_name, created_at)
     VALUES (?, ?, ?, ?, ?, ?)`,
  )
    .bind(voteId, targetType, targetId, user.email, user.name || null, now)
    .run()

  const created = (insertResult.meta?.changes ?? 0) > 0

  if (created) {
    await c.env.DB.prepare(`UPDATE ${countTable} SET upvote_count = upvote_count + 1 WHERE id = ?`)
      .bind(targetId)
      .run()
  }

  const row = await c.env.DB.prepare(`SELECT upvote_count FROM ${countTable} WHERE id = ?`)
    .bind(targetId)
    .first<{ upvote_count: number }>()

  return {
    target_type: targetType,
    target_id: targetId,
    upvote_count: row?.upvote_count ?? 0,
    created,
  }
}

discussionsRouter.post(
  '/:id/upvote',
  requireUserAuth,
  validate(PostIdSchema, 'param'),
  async (c) => {
    const { id } = c.req.valid('param')

    const post = await c.env.DB.prepare('SELECT id FROM discussion_posts WHERE id = ?')
      .bind(id)
      .first<{ id: string }>()
    if (!post) {
      throw notFound('Discussion post not found')
    }

    const data = await applyUpvote(c, 'post', id, 'discussion_posts')
    return c.json({ success: true, data })
  },
)

discussionsRouter.post(
  '/:id/comments/:commentId/upvote',
  requireUserAuth,
  validate(PostCommentIdSchema, 'param'),
  async (c) => {
    const { id, commentId } = c.req.valid('param')

    const comment = await c.env.DB.prepare('SELECT post_id FROM discussion_comments WHERE id = ?')
      .bind(commentId)
      .first<{ post_id: string }>()
    if (!comment) {
      throw notFound('Discussion comment not found')
    }
    if (comment.post_id !== id) {
      throw badRequest('Comment does not belong to this post')
    }

    const data = await applyUpvote(c, 'comment', commentId, 'discussion_comments')
    return c.json({ success: true, data })
  },
)

export default discussionsRouter
