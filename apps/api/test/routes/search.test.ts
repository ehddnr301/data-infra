import { SELF, env } from 'cloudflare:test'
import type { Env } from '@pseudolab/shared-types'
import { beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { z } from 'zod'
import { ProblemDetailSchema, expectJson, expectProblemJson } from '../helpers'

const db = (env as unknown as Env).DB
const RUN_ID = `${Date.now()}`

const DatasetHitSchema = z.object({
  id: z.string(),
  domain: z.enum(['github', 'discord', 'linkedin', 'members']),
  name: z.string(),
  description: z.string(),
  updated_at: z.string(),
})

const ColumnHitSchema = z.object({
  dataset_id: z.string(),
  dataset_name: z.string(),
  domain: z.enum(['github', 'discord', 'linkedin', 'members']),
  column_name: z.string(),
  data_type: z.string(),
  description: z.string().nullable(),
  is_pii: z.boolean(),
})

const GlossaryHitSchema = z.object({
  id: z.string(),
  domain: z.enum(['github', 'discord', 'linkedin', 'members']),
  term: z.string(),
  definition: z.string(),
  updated_at: z.string(),
})

const GroupSchema = <T extends z.ZodTypeAny>(item: T) =>
  z.object({
    total: z.number(),
    items: z.array(item),
  })

const SearchResponseSchema = z.object({
  success: z.literal(true),
  data: z.object({
    query: z.string(),
    type: z.enum(['all', 'dataset', 'column', 'glossary']),
    groups: z.object({
      datasets: GroupSchema(DatasetHitSchema),
      columns: GroupSchema(ColumnHitSchema),
      glossary: GroupSchema(GlossaryHitSchema),
    }),
  }),
  meta: z
    .object({
      cache: z.enum(['hit', 'miss']),
      tookMs: z.number(),
    })
    .optional(),
})

beforeAll(async () => {
  await db.exec(
    'CREATE TABLE IF NOT EXISTS catalog_datasets (id TEXT PRIMARY KEY, domain TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, schema_json TEXT, lineage_json TEXT, owner TEXT, tags TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);',
  )
  await db.exec(
    'CREATE TABLE IF NOT EXISTS catalog_columns (dataset_id TEXT NOT NULL, column_name TEXT NOT NULL, data_type TEXT NOT NULL, description TEXT, is_pii INTEGER NOT NULL DEFAULT 0, examples TEXT, PRIMARY KEY (dataset_id, column_name), FOREIGN KEY (dataset_id) REFERENCES catalog_datasets(id) ON DELETE CASCADE);',
  )
  await db.exec(
    "CREATE TABLE IF NOT EXISTS glossary_terms (id TEXT PRIMARY KEY, domain TEXT NOT NULL CHECK (domain IN ('github', 'discord', 'linkedin', 'members')), term TEXT NOT NULL, definition TEXT NOT NULL, related_terms TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(related_terms) AND json_type(related_terms) = 'array'), created_at TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??*'), updated_at TEXT NOT NULL CHECK (updated_at GLOB '????-??-??T??:??:??*'));",
  )
})

beforeEach(async () => {
  await db.exec('DELETE FROM catalog_columns;')
  await db.exec('DELETE FROM catalog_datasets;')
  await db.exec('DELETE FROM glossary_terms;')

  for (let i = 1; i <= 6; i += 1) {
    const datasetId = `ds.github.search.${RUN_ID}.${i}`
    await db
      .prepare(
        'INSERT INTO catalog_datasets (id, domain, name, description, schema_json, lineage_json, owner, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
      )
      .bind(
        datasetId,
        'github',
        `Search Dataset ${RUN_ID} ${i}`,
        `Dataset description ${RUN_ID} ${i}`,
        null,
        null,
        'qa',
        null,
        '2025-01-01T00:00:00.000Z',
        `2025-01-01T00:00:0${i}.000Z`,
      )
      .run()

    await db
      .prepare(
        'INSERT INTO catalog_columns (dataset_id, column_name, data_type, description, is_pii, examples) VALUES (?, ?, ?, ?, ?, ?)',
      )
      .bind(
        datasetId,
        `search_col_${RUN_ID}_${i}`,
        'TEXT',
        `Column description ${RUN_ID} ${i}`,
        0,
        null,
      )
      .run()

    await db
      .prepare(
        'INSERT INTO glossary_terms (id, domain, term, definition, related_terms, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
      )
      .bind(
        `0194f65f-7d75-7b1f-8e7a-1f3b2c4d5e${String(i).padStart(2, '0')}`,
        'github',
        `search-term-${RUN_ID}-${i}`,
        `Glossary definition ${RUN_ID} ${i}`,
        '[]',
        '2025-01-01T00:00:00.000Z',
        `2025-01-01T00:00:0${i}.000Z`,
      )
      .run()
  }

  await db
    .prepare(
      'INSERT INTO catalog_datasets (id, domain, name, description, schema_json, lineage_json, owner, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    )
    .bind(
      `ds.discord.search.${RUN_ID}.1`,
      'discord',
      `Search Dataset ${RUN_ID} discord`,
      `Dataset description ${RUN_ID} discord`,
      null,
      null,
      'qa',
      null,
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:08.000Z',
    )
    .run()

  await db
    .prepare(
      'INSERT INTO glossary_terms (id, domain, term, definition, related_terms, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
    )
    .bind(
      '0194f65f-7d75-7e1f-8b7b-4f3b2c4d5e6f',
      'discord',
      `search-term-${RUN_ID}-discord`,
      `Glossary definition ${RUN_ID} discord`,
      '[]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:09.000Z',
    )
    .run()
})

describe('GET /api/search', () => {
  it('returns grouped response and fixed preview for type=all', async () => {
    const res = await SELF.fetch(
      `http://example.com/api/search?q=${encodeURIComponent(RUN_ID)}&type=all&page=3&pageSize=1`,
    )

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = SearchResponseSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data.type).toBe('all')
    expect(parsed.data.data.groups.datasets.total).toBe(7)
    expect(parsed.data.data.groups.columns.total).toBe(6)
    expect(parsed.data.data.groups.glossary.total).toBe(7)
    expect(parsed.data.data.groups.datasets.items).toHaveLength(5)
    expect(parsed.data.data.groups.columns.items).toHaveLength(5)
    expect(parsed.data.data.groups.glossary.items).toHaveLength(5)
  })

  it('returns only selected group for single type while preserving 3-group envelope', async () => {
    const res = await SELF.fetch(
      `http://example.com/api/search?q=${encodeURIComponent(RUN_ID)}&type=dataset&page=2&pageSize=2`,
    )

    expect(res.status).toBe(200)
    const parsed = SearchResponseSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data.groups.datasets.total).toBe(7)
    expect(parsed.data.data.groups.datasets.items).toHaveLength(2)
    expect(parsed.data.data.groups.columns.total).toBe(0)
    expect(parsed.data.data.groups.columns.items).toHaveLength(0)
    expect(parsed.data.data.groups.glossary.total).toBe(0)
    expect(parsed.data.data.groups.glossary.items).toHaveLength(0)
  })

  it('applies domain filtering', async () => {
    const res = await SELF.fetch(
      `http://example.com/api/search?q=${encodeURIComponent(RUN_ID)}&type=glossary&domain=discord`,
    )

    expect(res.status).toBe(200)
    const parsed = SearchResponseSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data.groups.glossary.total).toBe(1)
    expect(parsed.data.data.groups.glossary.items[0]?.domain).toBe('discord')
  })

  it('returns 400 for invalid query parameters', async () => {
    const noQuery = await SELF.fetch('http://example.com/api/search')
    expect(noQuery.status).toBe(400)
    expectProblemJson(noQuery)

    const blankQuery = await SELF.fetch('http://example.com/api/search?q=   ')
    expect(blankQuery.status).toBe(400)
    expectProblemJson(blankQuery)

    const tooLong = await SELF.fetch(
      `http://example.com/api/search?q=${encodeURIComponent('가'.repeat(17))}`,
    )
    expect(tooLong.status).toBe(400)
    expectProblemJson(tooLong)

    const invalidType = await SELF.fetch('http://example.com/api/search?q=test&type=unknown')
    expect(invalidType.status).toBe(400)
    expectProblemJson(invalidType)

    const invalidPageSize = await SELF.fetch(
      'http://example.com/api/search?q=test&type=dataset&pageSize=101',
    )
    expect(invalidPageSize.status).toBe(400)
    expectProblemJson(invalidPageSize)

    const parsed = ProblemDetailSchema.safeParse(await invalidPageSize.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.type).toBe('/errors/validation')
  })

  it('returns cache hit for repeated identical requests', async () => {
    const url = `http://example.com/api/search?q=${encodeURIComponent(`cache-${RUN_ID}`)}&type=glossary`

    await db
      .prepare(
        'INSERT INTO glossary_terms (id, domain, term, definition, related_terms, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
      )
      .bind(
        `0194f65f-7d75-7d1f-af7b-3f3b2c4d${RUN_ID.slice(-4)}`,
        'github',
        `cache-${RUN_ID}`,
        'cache test',
        '[]',
        '2025-01-01T00:00:00.000Z',
        '2025-01-01T00:00:11.000Z',
      )
      .run()

    const first = await SELF.fetch(url)
    const firstBody = SearchResponseSchema.parse(await first.json())
    expect(firstBody.meta?.cache).toBe('miss')

    const second = await SELF.fetch(url)
    const secondBody = SearchResponseSchema.parse(await second.json())
    expect(secondBody.meta?.cache).toBe('hit')
  })

  it('falls back to D1 when KV read fails', async () => {
    type CacheLike = {
      get: (key: string, type?: 'text' | 'json') => Promise<unknown>
      put: (key: string, value: string, options?: { expirationTtl?: number }) => Promise<void>
    }

    const workerEnv = env as unknown as Env
    const cache = workerEnv.CACHE as unknown as CacheLike
    const originalGet = cache.get.bind(cache)

    cache.get = async () => {
      throw new Error('kv read failed')
    }

    try {
      const res = await SELF.fetch(
        `http://example.com/api/search?q=${encodeURIComponent(RUN_ID)}&type=dataset&page=1&pageSize=1`,
      )
      expect(res.status).toBe(200)
      const parsed = SearchResponseSchema.safeParse(await res.json())
      expect(parsed.success).toBe(true)
      if (!parsed.success) {
        return
      }
      expect(parsed.data.meta?.cache).toBe('miss')
      expect(parsed.data.data.groups.datasets.items).toHaveLength(1)
    } finally {
      cache.get = originalGet
    }
  })

  it('does not fail request when KV write fails', async () => {
    type CacheLike = {
      get: (key: string, type?: 'text' | 'json') => Promise<unknown>
      put: (key: string, value: string, options?: { expirationTtl?: number }) => Promise<void>
    }

    const workerEnv = env as unknown as Env
    const cache = workerEnv.CACHE as unknown as CacheLike
    const originalPut = cache.put.bind(cache)

    cache.put = async () => {
      throw new Error('kv write failed')
    }

    try {
      const res = await SELF.fetch(
        `http://example.com/api/search?q=${encodeURIComponent(RUN_ID)}&type=column&page=1&pageSize=2`,
      )
      expect(res.status).toBe(200)
      const parsed = SearchResponseSchema.safeParse(await res.json())
      expect(parsed.success).toBe(true)
      if (!parsed.success) {
        return
      }
      expect(parsed.data.data.groups.columns.items).toHaveLength(2)
    } finally {
      cache.put = originalPut
    }
  })
})
