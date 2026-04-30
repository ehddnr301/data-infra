import { SELF, env } from 'cloudflare:test'
import type { Env } from '@pseudolab/shared-types'
import { beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { z } from 'zod'
import { ProblemDetailSchema, apiSuccessSchema, expectJson, paginatedSchema } from '../helpers'

const db = (env as unknown as Env).DB
const INTERNAL_API_TOKEN = (env as unknown as Env).INTERNAL_API_TOKEN ?? 'test-internal-token'

const DATASET_ID = 'github.discussion-test.v1'
const LISTING_ID = 'listing-discussion-test'
const QUERY_ID = 'query-disc-1'
const ALT_DATASET_ID = 'github.discussion-other.v1'

const authedFetch = (
  url: string,
  init: RequestInit = {},
  user = 'agent@pseudolab.org',
  name = 'agent-bot',
) => {
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${INTERNAL_API_TOKEN}`)
  headers.set('X-User-Email', user)
  headers.set('X-User-Name', name)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return SELF.fetch(url, { ...init, headers })
}

const LinkedRefsSchema = z.object({
  dataset: z.object({ id: z.string(), name: z.string() }).nullable(),
  listing: z
    .object({ id: z.string(), domain: z.string(), slug: z.string(), title: z.string() })
    .nullable(),
  query_history: z.object({ id: z.string(), status: z.enum(['success', 'error']) }).nullable(),
})

const DiscussionPostBaseSchema = z.object({
  id: z.string(),
  title: z.string(),
  user_email: z.string(),
  user_name: z.string().nullable(),
  source: z.enum(['human', 'ai-auto', 'ai-assisted']),
  dataset_id: z.string().nullable(),
  listing_id: z.string().nullable(),
  query_history_id: z.string().nullable(),
  upvote_count: z.number(),
  comment_count: z.number(),
  created_at: z.string(),
  linked: LinkedRefsSchema,
})

const DiscussionPostSummarySchema = DiscussionPostBaseSchema.extend({
  excerpt: z.string(),
})

const DiscussionPostSchema = DiscussionPostBaseSchema.extend({
  content: z.string(),
})

const DiscussionCommentSchema = z.object({
  id: z.string(),
  post_id: z.string(),
  parent_comment_id: z.string().nullable(),
  user_email: z.string(),
  user_name: z.string().nullable(),
  source: z.enum(['human', 'ai-auto', 'ai-assisted']),
  content: z.string(),
  upvote_count: z.number(),
  created_at: z.string(),
})

const UpvoteSchema = z.object({
  target_type: z.enum(['post', 'comment']),
  target_id: z.string(),
  upvote_count: z.number(),
  created: z.boolean(),
})

beforeAll(async () => {
  await db.exec(
    'CREATE TABLE IF NOT EXISTS catalog_datasets (id TEXT PRIMARY KEY, domain TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, schema_json TEXT, lineage_json TEXT, owner TEXT, tags TEXT, purpose TEXT, limitations TEXT, usage_examples TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);',
  )
  await db.exec(
    'CREATE TABLE IF NOT EXISTS marketplace_listings (id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL UNIQUE, domain TEXT NOT NULL, slug TEXT NOT NULL, owner_id TEXT NOT NULL, title TEXT NOT NULL, subtitle TEXT, description TEXT NOT NULL, category TEXT NOT NULL, coverage_summary TEXT, update_frequency TEXT, documentation_url TEXT, last_verified_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (domain, slug));',
  )
  await db.exec(
    "CREATE TABLE IF NOT EXISTS query_history (id TEXT PRIMARY KEY, user_email TEXT NOT NULL, user_name TEXT, executed_sql TEXT NOT NULL, row_count INTEGER, execution_ms INTEGER, status TEXT NOT NULL DEFAULT 'success', error_message TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));",
  )
  await db.exec(
    "CREATE TABLE IF NOT EXISTS discussion_posts (id TEXT PRIMARY KEY, title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120), content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 4000), user_email TEXT NOT NULL, user_name TEXT, source TEXT NOT NULL DEFAULT 'ai-assisted' CHECK (source IN ('human','ai-auto','ai-assisted')), dataset_id TEXT, listing_id TEXT, query_history_id TEXT, upvote_count INTEGER NOT NULL DEFAULT 0, comment_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT (datetime('now')), CHECK (dataset_id IS NOT NULL OR listing_id IS NOT NULL OR query_history_id IS NOT NULL));",
  )
  await db.exec(
    "CREATE TABLE IF NOT EXISTS discussion_comments (id TEXT PRIMARY KEY, post_id TEXT NOT NULL, parent_comment_id TEXT, user_email TEXT NOT NULL, user_name TEXT, content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 2000), source TEXT NOT NULL DEFAULT 'ai-assisted' CHECK (source IN ('human','ai-auto','ai-assisted')), upvote_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT (datetime('now')));",
  )
  await db.exec(
    "CREATE TABLE IF NOT EXISTS discussion_votes (id TEXT PRIMARY KEY, target_type TEXT NOT NULL CHECK (target_type IN ('post','comment')), target_id TEXT NOT NULL, user_email TEXT NOT NULL, user_name TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')), UNIQUE (target_type, target_id, user_email));",
  )
})

beforeEach(async () => {
  await db.exec('DELETE FROM discussion_votes;')
  await db.exec('DELETE FROM discussion_comments;')
  await db.exec('DELETE FROM discussion_posts;')
  await db.exec('DELETE FROM query_history;')
  await db.exec('DELETE FROM marketplace_listings;')
  await db.exec('DELETE FROM catalog_datasets;')

  const datasetInsert = db.prepare(
    'INSERT INTO catalog_datasets (id, domain, name, description, schema_json, lineage_json, owner, tags, purpose, limitations, usage_examples, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
  )
  for (const dataset of [
    [
      DATASET_ID,
      'github',
      'Discussion Test Dataset',
      'Seed dataset for discussion route tests',
      null,
      null,
      'qa',
      null,
      null,
      null,
      null,
      '2026-01-01T00:00:00.000Z',
      '2026-01-01T00:00:00.000Z',
    ],
    [
      ALT_DATASET_ID,
      'github',
      'Alt Dataset',
      'Second dataset',
      null,
      null,
      'qa',
      null,
      null,
      null,
      null,
      '2026-01-01T00:00:00.000Z',
      '2026-01-01T00:00:00.000Z',
    ],
  ]) {
    await datasetInsert.bind(...dataset).run()
  }

  await db
    .prepare(
      'INSERT INTO marketplace_listings (id, dataset_id, domain, slug, owner_id, title, subtitle, description, category, coverage_summary, update_frequency, documentation_url, last_verified_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    )
    .bind(
      LISTING_ID,
      DATASET_ID,
      'github',
      'discussion-test.v1',
      'owner-x',
      'Discussion Test Listing',
      null,
      'desc',
      'engineering',
      null,
      null,
      null,
      null,
      '2026-01-01T00:00:00.000Z',
      '2026-01-01T00:00:00.000Z',
    )
    .run()

  await db
    .prepare(
      "INSERT INTO query_history (id, user_email, user_name, executed_sql, row_count, execution_ms, status, error_message, created_at) VALUES (?, ?, ?, ?, ?, ?, 'success', NULL, ?)",
    )
    .bind(
      QUERY_ID,
      'agent@pseudolab.org',
      'agent-bot',
      'SELECT 1',
      1,
      5,
      '2026-01-01T00:00:00.000Z',
    )
    .run()
})

async function createPost(overrides: Record<string, unknown> = {}, user = 'agent@pseudolab.org') {
  const body = {
    title: 'Default test title',
    content: 'Default test content',
    source: 'ai-assisted',
    dataset_id: DATASET_ID,
    ...overrides,
  }
  const res = await authedFetch(
    'http://example.com/api/discussions',
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
    user,
  )
  expect(res.status).toBe(201)
  const parsed = apiSuccessSchema(DiscussionPostSchema).parse(await res.json())
  return parsed.data
}

describe('discussions API', () => {
  it('creates a post linked to a dataset', async () => {
    const post = await createPost({ title: 'Dataset post', content: 'Body content' })
    expect(post.linked.dataset?.id).toBe(DATASET_ID)
    expect(post.linked.dataset?.name).toBe('Discussion Test Dataset')
    expect(post.linked.listing).toBeNull()
    expect(post.upvote_count).toBe(0)
    expect(post.comment_count).toBe(0)
  })

  it('rejects post creation without any link id', async () => {
    const res = await authedFetch('http://example.com/api/discussions', {
      method: 'POST',
      body: JSON.stringify({
        title: 'No link',
        content: 'No link body',
        source: 'ai-assisted',
      }),
    })
    expect(res.status).toBe(400)
    ProblemDetailSchema.parse(await res.json())
  })

  it('rejects post with unknown dataset_id', async () => {
    const res = await authedFetch('http://example.com/api/discussions', {
      method: 'POST',
      body: JSON.stringify({
        title: 'Bad link',
        content: 'Bad body',
        source: 'ai-assisted',
        dataset_id: 'no-such-dataset',
      }),
    })
    expect(res.status).toBe(404)
  })

  it('lists posts ordered by popular and latest', async () => {
    const a = await createPost({ title: 'A', content: 'a body' })
    const b = await createPost({
      title: 'B',
      content: 'b body',
      listing_id: LISTING_ID,
      dataset_id: null,
    })
    // Make B more popular
    await authedFetch(`http://example.com/api/discussions/${b.id}/upvote`, { method: 'POST' })
    await authedFetch(
      `http://example.com/api/discussions/${b.id}/upvote`,
      { method: 'POST' },
      'second@pseudolab.org',
      'second-bot',
    )

    const popularRes = await SELF.fetch('http://example.com/api/discussions?sort=popular')
    expect(popularRes.status).toBe(200)
    expectJson(popularRes)
    const popular = paginatedSchema(DiscussionPostSummarySchema).parse(await popularRes.json())
    expect(popular.data[0]?.id).toBe(b.id)
    expect(popular.data[1]?.id).toBe(a.id)

    const latestRes = await SELF.fetch('http://example.com/api/discussions?sort=latest')
    expect(latestRes.status).toBe(200)
    const latest = paginatedSchema(DiscussionPostSummarySchema).parse(await latestRes.json())
    expect(latest.data[0]?.id).toBe(b.id)
    expect(latest.data[1]?.id).toBe(a.id)
  })

  it('returns 404 for unknown post detail', async () => {
    const res = await SELF.fetch('http://example.com/api/discussions/missing')
    expect(res.status).toBe(404)
  })

  it('creates top-level and nested comments and increments comment_count', async () => {
    const post = await createPost()
    const top = await authedFetch(`http://example.com/api/discussions/${post.id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content: 'top', source: 'ai-assisted' }),
    })
    expect(top.status).toBe(201)
    const topComment = apiSuccessSchema(DiscussionCommentSchema).parse(await top.json()).data

    const nested = await authedFetch(`http://example.com/api/discussions/${post.id}/comments`, {
      method: 'POST',
      body: JSON.stringify({
        content: 'reply',
        source: 'ai-assisted',
        parent_comment_id: topComment.id,
      }),
    })
    expect(nested.status).toBe(201)
    const nestedComment = apiSuccessSchema(DiscussionCommentSchema).parse(await nested.json()).data
    expect(nestedComment.parent_comment_id).toBe(topComment.id)

    const detailRes = await SELF.fetch(`http://example.com/api/discussions/${post.id}`)
    const detail = apiSuccessSchema(DiscussionPostSchema).parse(await detailRes.json()).data
    expect(detail.comment_count).toBe(2)
  })

  it('rejects nested comment whose parent belongs to a different post', async () => {
    const postA = await createPost({ title: 'A' })
    const postB = await createPost({ title: 'B' })
    const top = await authedFetch(`http://example.com/api/discussions/${postA.id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content: 'top', source: 'ai-assisted' }),
    })
    const topComment = apiSuccessSchema(DiscussionCommentSchema).parse(await top.json()).data

    const res = await authedFetch(`http://example.com/api/discussions/${postB.id}/comments`, {
      method: 'POST',
      body: JSON.stringify({
        content: 'reply',
        source: 'ai-assisted',
        parent_comment_id: topComment.id,
      }),
    })
    expect(res.status).toBe(400)
  })

  it('returns comments flat ordered oldest-first', async () => {
    const post = await createPost()
    await authedFetch(`http://example.com/api/discussions/${post.id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content: 'first', source: 'ai-assisted' }),
    })
    await authedFetch(`http://example.com/api/discussions/${post.id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content: 'second', source: 'ai-assisted' }),
    })

    const res = await SELF.fetch(`http://example.com/api/discussions/${post.id}/comments`)
    expect(res.status).toBe(200)
    const list = apiSuccessSchema(z.array(DiscussionCommentSchema)).parse(await res.json()).data
    expect(list).toHaveLength(2)
    expect(list[0]?.content).toBe('first')
    expect(list[1]?.content).toBe('second')
  })

  it('post upvote is idempotent per user and increments count once', async () => {
    const post = await createPost()
    const first = await authedFetch(`http://example.com/api/discussions/${post.id}/upvote`, {
      method: 'POST',
    })
    expect(first.status).toBe(200)
    const firstBody = apiSuccessSchema(UpvoteSchema).parse(await first.json()).data
    expect(firstBody.created).toBe(true)
    expect(firstBody.upvote_count).toBe(1)

    const second = await authedFetch(`http://example.com/api/discussions/${post.id}/upvote`, {
      method: 'POST',
    })
    const secondBody = apiSuccessSchema(UpvoteSchema).parse(await second.json()).data
    expect(secondBody.created).toBe(false)
    expect(secondBody.upvote_count).toBe(1)
  })

  it('comment upvote is idempotent per user', async () => {
    const post = await createPost()
    const created = await authedFetch(`http://example.com/api/discussions/${post.id}/comments`, {
      method: 'POST',
      body: JSON.stringify({ content: 'hi', source: 'ai-assisted' }),
    })
    const comment = apiSuccessSchema(DiscussionCommentSchema).parse(await created.json()).data

    const path = `http://example.com/api/discussions/${post.id}/comments/${comment.id}/upvote`
    const r1 = await authedFetch(path, { method: 'POST' })
    const b1 = apiSuccessSchema(UpvoteSchema).parse(await r1.json()).data
    expect(b1.created).toBe(true)
    expect(b1.upvote_count).toBe(1)

    const r2 = await authedFetch(path, { method: 'POST' })
    const b2 = apiSuccessSchema(UpvoteSchema).parse(await r2.json()).data
    expect(b2.created).toBe(false)
    expect(b2.upvote_count).toBe(1)
  })
})
