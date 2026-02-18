import { env, SELF } from 'cloudflare:test'
import { beforeAll, describe, expect, it } from 'vitest'
import type { Env } from '@pseudolab/shared-types'
import {
  expectJson,
  expectProblemJson,
  paginatedSchema,
  ProblemDetailSchema,
} from '../helpers'

const db = (env as unknown as Env).DB

beforeAll(async () => {
  await db.exec(
    'CREATE TABLE IF NOT EXISTS catalog_datasets (id TEXT PRIMARY KEY, domain TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, schema_json TEXT, glossary_json TEXT, lineage_json TEXT, owner TEXT, tags TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);'
  )
  await db.exec(
    'CREATE TABLE IF NOT EXISTS catalog_columns (dataset_id TEXT NOT NULL, column_name TEXT NOT NULL, data_type TEXT NOT NULL, description TEXT, is_pii INTEGER NOT NULL DEFAULT 0, examples TEXT, PRIMARY KEY (dataset_id, column_name), FOREIGN KEY (dataset_id) REFERENCES catalog_datasets(id) ON DELETE CASCADE);'
  )
})

describe('GET /api/catalog/datasets', () => {
  it('returns paginated dataset list', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets')

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = paginatedSchema(ProblemDetailSchema.passthrough()).safeParse(
      await res.json(),
    )
    expect(parsed.success).toBe(true)
  })
})

describe('GET /api/catalog/datasets/:id', () => {
  it('returns not found for non-existent dataset', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets/non-existent')

    expect(res.status).toBe(404)
    expectProblemJson(res)

    const parsed = ProblemDetailSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
  })
})

describe('GET /api/catalog/datasets/:id/columns', () => {
  it('returns not found for non-existent dataset', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets/non-existent/columns')

    expect(res.status).toBe(404)
    expectProblemJson(res)

    const parsed = ProblemDetailSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
  })
})

describe('query validation', () => {
  it('returns 400 for invalid pageSize', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets?pageSize=-1')

    expect(res.status).toBe(400)
    expectProblemJson(res)

    const parsed = ProblemDetailSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }
    expect(parsed.data.type).toBe('/errors/validation')
  })
})
