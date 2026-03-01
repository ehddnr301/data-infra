import { SELF, env } from 'cloudflare:test'
import type { Env } from '@pseudolab/shared-types'
import { beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { z } from 'zod'
import { ProblemDetailSchema, expectJson, expectProblemJson, paginatedSchema } from '../helpers'

const db = (env as unknown as Env).DB

const TERM_ALPHA_ID = '0194f65f-7d75-7b1f-8e7a-1f3b2c4d5e6f'
const TERM_BETA_ID = '0194f65f-7d75-7c1f-9a7b-2f3b2c4d5e6f'
const TERM_GAMMA_ID = '0194f65f-7d75-7d1f-af7b-3f3b2c4d5e6f'
const TERM_DISCORD_ID = '0194f65f-7d75-7e1f-8b7b-4f3b2c4d5e6f'

const GlossaryTermSchema = z.object({
  id: z.string(),
  domain: z.enum(['github', 'discord', 'linkedin', 'members']),
  term: z.string(),
  definition: z.string(),
  related_terms: z.array(z.string()),
  created_at: z.string(),
  updated_at: z.string(),
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
  await db.exec(
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_glossary_terms_domain_term ON glossary_terms(domain, term);',
  )
  await db.exec(
    "CREATE TABLE IF NOT EXISTS glossary_backfill_conflicts (domain TEXT NOT NULL, term TEXT NOT NULL, dataset_id TEXT NOT NULL, reason TEXT NOT NULL, logged_at TEXT NOT NULL CHECK (logged_at GLOB '????-??-??T??:??:??*'));",
  )
})

beforeEach(async () => {
  await db.exec('DELETE FROM catalog_columns;')
  await db.exec('DELETE FROM catalog_datasets;')
  await db.exec('DELETE FROM glossary_terms;')
  await db.exec('DELETE FROM glossary_backfill_conflicts;')

  await db
    .prepare(
      'INSERT INTO catalog_datasets (id, domain, name, description, schema_json, lineage_json, owner, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    )
    .bind(
      'ds.github.repo.v1',
      'github',
      'GitHub Repo Dataset',
      'Dataset for tests',
      null,
      null,
      'qa',
      '["github"]',
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    )
    .run()
})

async function insertGlossaryTerm(input: {
  id: string
  domain: 'github' | 'discord' | 'linkedin' | 'members'
  term: string
  definition: string
  related_terms?: string[]
}) {
  await db
    .prepare(
      'INSERT INTO glossary_terms (id, domain, term, definition, related_terms, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
    )
    .bind(
      input.id,
      input.domain,
      input.term,
      input.definition,
      JSON.stringify(input.related_terms ?? []),
      '2025-01-01T00:00:00.000Z',
      '2025-01-01T00:00:00.000Z',
    )
    .run()
}

describe('datasets routes', () => {
  it('returns paginated dataset list', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets')

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = paginatedSchema(z.object({}).passthrough()).safeParse(await res.json())
    expect(parsed.success).toBe(true)
  })

  it('returns 404 for non-existent dataset', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets/non-existent')

    expect(res.status).toBe(404)
    expectProblemJson(res)
  })

  it('returns 404 for non-existent dataset columns', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets/non-existent/columns')

    expect(res.status).toBe(404)
    expectProblemJson(res)
  })

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

describe('glossary CRUD', () => {
  it('GET /api/catalog/glossary returns paginated list', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'actor',
      definition: 'GitHub event actor',
    })

    const res = await SELF.fetch('http://example.com/api/catalog/glossary?page=1&pageSize=10')
    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = paginatedSchema(GlossaryTermSchema).safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data).toHaveLength(1)
    expect(parsed.data.data[0]?.id).toBe(TERM_ALPHA_ID)
  })

  it('GET /api/catalog/glossary filters by q and domain', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'actor',
      definition: 'GitHub event actor',
    })
    await insertGlossaryTerm({
      id: TERM_DISCORD_ID,
      domain: 'discord',
      term: 'actor',
      definition: 'Discord actor',
    })

    const res = await SELF.fetch('http://example.com/api/catalog/glossary?q=GitHub&domain=github')
    expect(res.status).toBe(200)

    const parsed = paginatedSchema(GlossaryTermSchema).safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }

    expect(parsed.data.data).toHaveLength(1)
    expect(parsed.data.data[0]?.domain).toBe('github')
  })

  it('GET /api/catalog/glossary/:id returns item and 404 for missing', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'actor',
      definition: 'GitHub event actor',
    })

    const found = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`)
    expect(found.status).toBe(200)

    const foundBody = z
      .object({
        success: z.literal(true),
        data: GlossaryTermSchema,
      })
      .safeParse(await found.json())
    expect(foundBody.success).toBe(true)

    const missing = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_BETA_ID}`)
    expect(missing.status).toBe(404)
    expectProblemJson(missing)
  })

  it('POST creates term and invalid body returns 400', async () => {
    const created = await SELF.fetch('http://example.com/api/catalog/glossary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        domain: 'github',
        term: 'repo',
        definition: 'Repository',
      }),
    })
    expect(created.status).toBe(201)

    const createdBody = z
      .object({
        success: z.literal(true),
        data: GlossaryTermSchema,
      })
      .safeParse(await created.json())
    expect(createdBody.success).toBe(true)

    const invalid = await SELF.fetch('http://example.com/api/catalog/glossary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        domain: 'github',
        term: '',
        definition: '',
      }),
    })
    expect(invalid.status).toBe(400)
    expectProblemJson(invalid)
  })

  it('POST duplicate (domain, term) returns 409 ProblemDetail', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'repo',
      definition: 'Repository',
    })

    const res = await SELF.fetch('http://example.com/api/catalog/glossary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        domain: 'github',
        term: 'repo',
        definition: 'Another definition',
      }),
    })

    expect(res.status).toBe(409)
    expectProblemJson(res)
    const parsed = ProblemDetailSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }
    expect(parsed.data.type).toBe('/errors/conflict')
  })

  it('PUT updates term and empty body returns 400', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'repo',
      definition: 'Repository',
    })

    const updated = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ definition: 'Repository entity' }),
    })
    expect(updated.status).toBe(200)

    const invalid = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    expect(invalid.status).toBe(400)
    expectProblemJson(invalid)
  })

  it('DELETE removes term and subsequent GET returns 404', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'repo',
      definition: 'Repository',
    })

    const deleted = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`, {
      method: 'DELETE',
    })
    expect(deleted.status).toBe(200)
    expectJson(deleted)

    const deletedBody = z
      .object({
        success: z.literal(true),
        data: z.object({
          id: z.string(),
          deleted: z.literal(true),
        }),
      })
      .safeParse(await deleted.json())
    expect(deletedBody.success).toBe(true)

    const after = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`)
    expect(after.status).toBe(404)
  })

  it('related_terms unknown id returns 400', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/glossary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        domain: 'github',
        term: 'repo',
        definition: 'Repository',
        related_terms: [TERM_BETA_ID],
      }),
    })

    expect(res.status).toBe(400)
    expectProblemJson(res)
  })

  it('related_terms self-reference returns 400', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'repo',
      definition: 'Repository',
    })

    const res = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ related_terms: [TERM_ALPHA_ID] }),
    })

    expect(res.status).toBe(400)
    expectProblemJson(res)
  })

  it('related_terms duplicate ids return 400', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'repo',
      definition: 'Repository',
    })
    await insertGlossaryTerm({
      id: TERM_BETA_ID,
      domain: 'github',
      term: 'issue',
      definition: 'Issue',
    })

    const res = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ related_terms: [TERM_BETA_ID, TERM_BETA_ID] }),
    })

    expect(res.status).toBe(400)
    expectProblemJson(res)
  })

  it('related_terms cross-domain reference returns 400', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'repo',
      definition: 'Repository',
    })
    await insertGlossaryTerm({
      id: TERM_DISCORD_ID,
      domain: 'discord',
      term: 'channel',
      definition: 'Discord channel',
    })

    const res = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ related_terms: [TERM_DISCORD_ID] }),
    })

    expect(res.status).toBe(400)
    expectProblemJson(res)
  })

  it('delete removes reverse references', async () => {
    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'repo',
      definition: 'Repository',
      related_terms: [],
    })
    await insertGlossaryTerm({
      id: TERM_BETA_ID,
      domain: 'github',
      term: 'issue',
      definition: 'Issue',
      related_terms: [TERM_ALPHA_ID, TERM_GAMMA_ID, TERM_ALPHA_ID],
    })
    await insertGlossaryTerm({
      id: TERM_GAMMA_ID,
      domain: 'github',
      term: 'pull_request',
      definition: 'Pull request',
      related_terms: [TERM_ALPHA_ID],
    })

    const deleted = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_ALPHA_ID}`, {
      method: 'DELETE',
    })
    expect(deleted.status).toBe(200)

    const beta = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_BETA_ID}`)
    const betaBody = z
      .object({
        success: z.literal(true),
        data: GlossaryTermSchema,
      })
      .safeParse(await beta.json())
    expect(betaBody.success).toBe(true)
    if (!betaBody.success) {
      return
    }
    expect(betaBody.data.data.related_terms).toEqual([TERM_GAMMA_ID])

    const gamma = await SELF.fetch(`http://example.com/api/catalog/glossary/${TERM_GAMMA_ID}`)
    const gammaBody = z
      .object({
        success: z.literal(true),
        data: GlossaryTermSchema,
      })
      .safeParse(await gamma.json())
    expect(gammaBody.success).toBe(true)
    if (!gammaBody.success) {
      return
    }
    expect(gammaBody.data.data.related_terms).toEqual([])
  })

  it('UUIDv7 format validation works for param and body array', async () => {
    const invalidParam = await SELF.fetch('http://example.com/api/catalog/glossary/not-a-v7-id')
    expect(invalidParam.status).toBe(400)
    expectProblemJson(invalidParam)

    const invalidBody = await SELF.fetch('http://example.com/api/catalog/glossary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        domain: 'github',
        term: 'repo',
        definition: 'Repository',
        related_terms: ['550e8400-e29b-41d4-a716-446655440000'],
      }),
    })
    expect(invalidBody.status).toBe(400)
    expectProblemJson(invalidBody)
  })
})

describe('backfill migration validation', () => {
  it('validates target/inserted/skip counts', async () => {
    await db.exec('DROP TABLE IF EXISTS catalog_datasets;')
    await db.exec(
      'CREATE TABLE catalog_datasets (id TEXT PRIMARY KEY, domain TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, schema_json TEXT, glossary_json TEXT, lineage_json TEXT, owner TEXT, tags TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);',
    )
    await db.exec('DELETE FROM glossary_terms;')
    await db.exec('DELETE FROM glossary_backfill_conflicts;')

    await db
      .prepare(
        'INSERT INTO catalog_datasets (id, domain, name, description, schema_json, glossary_json, lineage_json, owner, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
      )
      .bind(
        'ds.github.1',
        'github',
        'Dataset 1',
        'desc',
        null,
        '{"repo":"Repository","issue":"Issue"}',
        null,
        null,
        null,
        '2025-01-01T00:00:00.000Z',
        '2025-01-01T00:00:00.000Z',
      )
      .run()

    await db
      .prepare(
        'INSERT INTO catalog_datasets (id, domain, name, description, schema_json, glossary_json, lineage_json, owner, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
      )
      .bind(
        'ds.github.2',
        'github',
        'Dataset 2',
        'desc',
        null,
        '{"repo":"Repository duplicate","actor":"Actor"}',
        null,
        null,
        null,
        '2025-01-01T00:00:00.000Z',
        '2025-01-01T00:00:00.000Z',
      )
      .run()

    await insertGlossaryTerm({
      id: TERM_ALPHA_ID,
      domain: 'github',
      term: 'actor',
      definition: 'Existing actor',
    })

    await db.exec(
      "INSERT INTO glossary_backfill_conflicts (domain, term, dataset_id, reason, logged_at) SELECT d.domain, j.key, d.id, 'duplicate-in-source', strftime('%Y-%m-%dT%H:%M:%fZ', 'now') FROM catalog_datasets d JOIN json_each(d.glossary_json) j WHERE d.glossary_json IS NOT NULL AND json_valid(d.glossary_json) AND json_type(d.glossary_json) = 'object' AND (SELECT COUNT(*) FROM catalog_datasets d2 JOIN json_each(d2.glossary_json) j2 ON d2.glossary_json IS NOT NULL AND json_valid(d2.glossary_json) AND json_type(d2.glossary_json) = 'object' AND d2.domain = d.domain AND j2.key = j.key) > 1;",
    )
    await db.exec(
      "INSERT INTO glossary_backfill_conflicts (domain, term, dataset_id, reason, logged_at) SELECT d.domain, j.key, d.id, 'already-exists', strftime('%Y-%m-%dT%H:%M:%fZ', 'now') FROM catalog_datasets d JOIN json_each(d.glossary_json) j WHERE d.glossary_json IS NOT NULL AND json_valid(d.glossary_json) AND json_type(d.glossary_json) = 'object' AND EXISTS (SELECT 1 FROM glossary_terms gt WHERE gt.domain = d.domain AND gt.term = j.key);",
    )
    await db.exec(
      "INSERT INTO glossary_terms (id, domain, term, definition, related_terms, created_at, updated_at) SELECT lower(substr(hex(randomblob(4)), 1, 8) || '-' || substr(hex(randomblob(2)), 1, 4) || '-' || '7' || substr(hex(randomblob(2)), 2, 3) || '-' || substr('89ab', (abs(random()) % 4) + 1, 1) || substr(hex(randomblob(2)), 2, 3) || '-' || substr(hex(randomblob(6)), 1, 12)) AS id, d.domain, j.key AS term, CAST(j.value AS TEXT) AS definition, '[]' AS related_terms, strftime('%Y-%m-%dT%H:%M:%fZ', 'now') AS created_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now') AS updated_at FROM catalog_datasets d JOIN json_each(d.glossary_json) j WHERE d.glossary_json IS NOT NULL AND json_valid(d.glossary_json) AND json_type(d.glossary_json) = 'object' ON CONFLICT(domain, term) DO NOTHING;",
    )

    const eligible = (await db
      .prepare(
        "SELECT COUNT(*) as total FROM catalog_datasets d JOIN json_each(d.glossary_json) j WHERE d.glossary_json IS NOT NULL AND json_valid(d.glossary_json) AND json_type(d.glossary_json) = 'object'",
      )
      .first()) as { total: number } | null
    const inserted = (await db
      .prepare(
        "SELECT COUNT(*) as total FROM glossary_terms WHERE term IN ('repo', 'issue', 'actor') AND domain = 'github'",
      )
      .first()) as { total: number } | null
    const conflicts = (await db
      .prepare('SELECT COUNT(*) as total FROM glossary_backfill_conflicts WHERE domain = ?')
      .bind('github')
      .first()) as { total: number } | null

    expect(eligible?.total ?? 0).toBe(4)
    expect(inserted?.total ?? 0).toBe(3)
    expect(conflicts?.total ?? 0).toBeGreaterThanOrEqual(2)
  })
})
