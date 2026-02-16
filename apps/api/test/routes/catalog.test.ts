import { SELF } from 'cloudflare:test'
import { describe, expect, it } from 'vitest'
import {
  expectJson,
  expectProblemJson,
  paginatedSchema,
  ProblemDetailSchema,
} from '../helpers'

describe('GET /api/catalog/datasets', () => {
  it('returns paginated dataset list stub response', async () => {
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
  it('returns not found in stub state', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets/1')

    expect(res.status).toBe(404)
    expectProblemJson(res)

    const parsed = ProblemDetailSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
  })
})

describe('GET /api/catalog/datasets/:id/columns', () => {
  it('returns not found in stub state', async () => {
    const res = await SELF.fetch('http://example.com/api/catalog/datasets/1/columns')

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
