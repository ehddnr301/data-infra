import { SELF } from 'cloudflare:test'
import { describe, expect, it } from 'vitest'
import { expectProblemJson, ProblemDetailSchema } from './helpers'

describe('CORS', () => {
  it('returns cors headers on preflight request', async () => {
    const res = await SELF.fetch('http://example.com/api/health', {
      method: 'OPTIONS',
      headers: {
        Origin: 'http://localhost:5173',
        'Access-Control-Request-Method': 'GET',
      },
    })

    expect(res.headers.get('access-control-allow-origin')).toBeTruthy()
  })

  it('returns cors headers on normal request', async () => {
    const res = await SELF.fetch('http://example.com/api/health')
    expect(res.headers.get('access-control-allow-origin')).toBeTruthy()
  })
})

describe('Not Found', () => {
  it('returns rfc7807 problem detail for unknown route', async () => {
    const res = await SELF.fetch('http://example.com/api/nonexistent')

    expect(res.status).toBe(404)
    expectProblemJson(res)

    const parsed = ProblemDetailSchema.safeParse(await res.json())
    expect(parsed.success).toBe(true)
    if (!parsed.success) {
      return
    }
    expect(parsed.data.status).toBe(404)
    expect(parsed.data.type).toBe('/errors/not-found')
  })
})
