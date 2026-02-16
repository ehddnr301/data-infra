import { SELF } from 'cloudflare:test'
import { describe, expect, it } from 'vitest'
import {
  apiSuccessSchema,
  expectJson,
  expectProblemJson,
  paginatedSchema,
  ProblemDetailSchema,
} from '../helpers'

describe('GET /api/github/events', () => {
  it('returns paginated stub response', async () => {
    const res = await SELF.fetch('http://example.com/api/github/events')

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = paginatedSchema(ProblemDetailSchema.passthrough()).safeParse(
      await res.json(),
    )
    expect(parsed.success).toBe(true)
  })
})

describe('GET /api/github/events/:id', () => {
  it('returns not found in stub state', async () => {
    const res = await SELF.fetch('http://example.com/api/github/events/1')

    expect(res.status).toBe(404)
    expectProblemJson(res)

    const parsed = ProblemDetailSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
  })
})

describe('GET /api/github/stats/daily', () => {
  it('returns success list stub response', async () => {
    const res = await SELF.fetch('http://example.com/api/github/stats/daily')

    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = apiSuccessSchema(ProblemDetailSchema.array()).safeParse(
      await res.json(),
    )
    expect(parsed.success).toBe(true)
  })
})

describe('query validation', () => {
  it('returns 400 for invalid pageSize', async () => {
    const res = await SELF.fetch('http://example.com/api/github/events?pageSize=abc')

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
