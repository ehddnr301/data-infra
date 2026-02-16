import { SELF } from 'cloudflare:test'
import { describe, expect, it } from 'vitest'
import { expectJson, LivenessSchema, ReadinessSchema } from './helpers'

describe('GET /api/health', () => {
  it('returns liveness response contract', async () => {
    const res = await SELF.fetch('http://example.com/api/health')
    expect(res.status).toBe(200)
    expectJson(res)

    const parsed = LivenessSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }
    expect(Number.isNaN(Date.parse(parsed.data.timestamp))).toBe(false)
  })
})

describe('GET /api/health/ready', () => {
  it('returns readiness response contract', async () => {
    const res = await SELF.fetch('http://example.com/api/health/ready')
    expect([200, 503]).toContain(res.status)
    expectJson(res)

    const parsed = ReadinessSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }
    expect(parsed.data.checks.d1.status).toBeDefined()
    expect(parsed.data.checks.r2.status).toBeDefined()
    expect(parsed.data.checks.kv.status).toBeDefined()
  })
})
