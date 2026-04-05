import { zValidator } from '@hono/zod-validator'
import type { QueryHistoryEntry } from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { z } from 'zod'
import { AppError, notFound, validationError } from '../../lib/errors'
import { nanoid } from '../../lib/id'
import type { AuthEnv } from '../../middleware/user-auth'
import { requireUserAuth } from '../../middleware/user-auth'
import { PREVIEW_SOURCE_BY_DATASET_ID } from '../catalog/preview-sources'

const QUERY_TIMEOUT_MS = 5000
const MAX_LIMIT = 100

const FORBIDDEN_KEYWORDS = /\b(INSERT|UPDATE|DELETE|DROP|ALTER|ATTACH|PRAGMA|CREATE)\b/i

const ALLOWED_TABLES = new Set(
  Object.values(PREVIEW_SOURCE_BY_DATASET_ID).map((s) => s.table.toLowerCase()),
)

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

const SqlQuerySchema = z.object({
  sql: z.string().trim().min(1).max(10000),
})

const HistoryQuerySchema = z.object({
  user: z.string().optional(),
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
})

const HistoryIdSchema = z.object({
  id: z.string().min(1).max(30),
})

// --- Helpers ---

function enforceLimit(sql: string, maxLimit: number): string {
  const limitMatch = sql.match(/\bLIMIT\s+(\d+)\s*$/i)
  if (!limitMatch) {
    return `${sql} LIMIT ${maxLimit}`
  }
  const limitValue = limitMatch[1]
  const currentLimit = limitValue ? Number.parseInt(limitValue, 10) : 0
  if (currentLimit > maxLimit) {
    return sql.replace(/\bLIMIT\s+\d+\s*$/i, `LIMIT ${maxLimit}`)
  }
  return sql
}

function extractTableNames(sql: string): string[] {
  const tables: string[] = []
  const fromJoinPattern = /\b(?:FROM|JOIN)\s+([a-zA-Z_]\w*)/gi
  for (const match of sql.matchAll(fromJoinPattern)) {
    const tableName = match[1]
    if (tableName) {
      tables.push(tableName.toLowerCase())
    }
  }
  return tables
}

// --- Router ---

const queryRouter = new Hono<AuthEnv>()
queryRouter.use('*', requireUserAuth)

// POST /api/query — Execute read-only SQL
queryRouter.post('/', validateBody(SqlQuerySchema), async (c) => {
  const { sql } = c.req.valid('json')
  const user = c.get('user')
  const startTime = Date.now()

  // Security Step 1: Reject semicolons
  if (sql.includes(';')) {
    throw new AppError(
      400,
      'Forbidden Statement',
      '/errors/forbidden-statement',
      'Multi-statement queries (semicolons) are not allowed',
    )
  }

  // Security Step 2: Keyword blocklist
  if (FORBIDDEN_KEYWORDS.test(sql)) {
    throw new AppError(
      400,
      'Forbidden Statement',
      '/errors/forbidden-statement',
      'Only SELECT statements are allowed',
    )
  }

  // Best-effort table whitelist check
  const tables = extractTableNames(sql)
  const unknownTables = tables.filter((t) => !ALLOWED_TABLES.has(t))
  if (unknownTables.length > 0) {
    throw new AppError(
      400,
      'Unknown Table',
      '/errors/unknown-table',
      `Table(s) not found in catalog: ${unknownTables.join(', ')}`,
    )
  }

  // LIMIT enforcement
  const finalSql = enforceLimit(sql, MAX_LIMIT)

  // Execute with timeout
  let result: { results: Record<string, unknown>[]; success: boolean }
  try {
    const queryPromise = c.env.DB.prepare(finalSql).all()
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(
        () =>
          reject(
            new AppError(408, 'Query Timeout', '/errors/timeout', 'Query exceeded 5 second limit'),
          ),
        QUERY_TIMEOUT_MS,
      ),
    )
    result = await Promise.race([queryPromise, timeoutPromise])
  } catch (err) {
    const executionMs = Date.now() - startTime
    const errorMessage = err instanceof Error ? err.message : 'Unknown error'

    // Record failed query in history (fire-and-forget)
    c.executionCtx.waitUntil(
      c.env.DB.prepare(
        `INSERT INTO query_history (id, user_email, user_name, executed_sql, row_count, execution_ms, status, error_message)
         VALUES (?, ?, ?, ?, NULL, ?, 'error', ?)`,
      )
        .bind(nanoid(), user.email, user.name || null, finalSql, executionMs, errorMessage)
        .run()
        .catch(() => {}),
    )

    if (err instanceof AppError) throw err
    throw new AppError(400, 'Query Error', '/errors/query-error', errorMessage)
  }

  const executionMs = Date.now() - startTime
  const rows = result.results
  const firstRow = rows[0]
  const columns = firstRow ? Object.keys(firstRow) : []

  // Record successful query in history (fire-and-forget)
  c.executionCtx.waitUntil(
    c.env.DB.prepare(
      `INSERT INTO query_history (id, user_email, user_name, executed_sql, row_count, execution_ms, status)
       VALUES (?, ?, ?, ?, ?, ?, 'success')`,
    )
      .bind(nanoid(), user.email, user.name || null, finalSql, rows.length, executionMs)
      .run()
      .catch(() => {}),
  )

  return c.json({
    success: true,
    data: {
      columns,
      rows,
      row_count: rows.length,
      truncated: rows.length >= MAX_LIMIT,
      executed_sql: finalSql,
    },
    meta: { execution_ms: executionMs },
  })
})

// GET /api/query/history — List query history (paginated)
queryRouter.get('/history', validate(HistoryQuerySchema, 'query'), async (c) => {
  const query = c.req.valid('query')
  const page = query.page ?? 1
  const pageSize = query.pageSize ?? 20
  const offset = (page - 1) * pageSize

  const whereClause = query.user ? 'WHERE user_email = ?' : ''
  const bindings = query.user ? [query.user] : []

  const countResult = (await c.env.DB.prepare(
    `SELECT COUNT(*) as total FROM query_history ${whereClause}`,
  )
    .bind(...bindings)
    .first()) as { total: number } | null

  const total = countResult?.total ?? 0
  const totalPages = Math.ceil(total / pageSize)

  const rows = await c.env.DB.prepare(
    `SELECT id, user_email, user_name, executed_sql, row_count, execution_ms, status, error_message, created_at
     FROM query_history ${whereClause}
     ORDER BY created_at DESC LIMIT ? OFFSET ?`,
  )
    .bind(...bindings, pageSize, offset)
    .all<QueryHistoryEntry>()

  return c.json({
    success: true,
    data: rows.results,
    pagination: { page, pageSize, total, totalPages },
  })
})

// GET /api/query/history/:id — Single query detail
queryRouter.get('/history/:id', validate(HistoryIdSchema, 'param'), async (c) => {
  const { id } = c.req.valid('param')

  const row = await c.env.DB.prepare(
    `SELECT id, user_email, user_name, executed_sql, row_count, execution_ms, status, error_message, created_at
     FROM query_history WHERE id = ?`,
  )
    .bind(id)
    .first<QueryHistoryEntry>()

  if (!row) {
    throw notFound('Query history entry not found')
  }

  return c.json({ success: true, data: row })
})

export default queryRouter
