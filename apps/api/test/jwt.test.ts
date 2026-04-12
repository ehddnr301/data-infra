import { describe, expect, it } from 'vitest'
import { type JwtPayload, signJwt, verifyJwt } from '../src/lib/jwt'

const SECRET = 'test-secret-key-for-jwt-testing-only'
const OTHER_SECRET = 'different-secret-key'

const testPayload = {
  email: 'test@example.com',
  name: 'Test User',
  role: 'member' as const,
  picture: 'https://example.com/photo.jpg',
}

describe('JWT utility', () => {
  it('signJwt produces a three-part token', async () => {
    const token = await signJwt(testPayload, SECRET)
    const parts = token.split('.')
    expect(parts.length).toBe(3)
    expect(parts[0]?.length).toBeGreaterThan(0)
    expect(parts[1]?.length).toBeGreaterThan(0)
    expect(parts[2]?.length).toBeGreaterThan(0)
  })

  it('verifyJwt correctly verifies a valid token', async () => {
    const token = await signJwt(testPayload, SECRET)
    const payload = await verifyJwt(token, SECRET)

    expect(payload).not.toBeNull()
    expect(payload?.email).toBe('test@example.com')
    expect(payload?.name).toBe('Test User')
    expect(payload?.role).toBe('member')
    expect(payload?.picture).toBe('https://example.com/photo.jpg')
    expect(payload?.iat).toBeTypeOf('number')
    expect(payload?.exp).toBeTypeOf('number')
    expect(payload?.exp).toBeGreaterThan(payload?.iat)
  })

  it('verifyJwt returns null for a different secret', async () => {
    const token = await signJwt(testPayload, SECRET)
    const payload = await verifyJwt(token, OTHER_SECRET)
    expect(payload).toBeNull()
  })

  it('verifyJwt returns null for a tampered payload', async () => {
    const token = await signJwt(testPayload, SECRET)
    const parts = token.split('.')

    // Tamper with the payload (change one character)
    const tamperedPayload = `${parts[0]}.${parts[1]?.slice(0, -1)}X.${parts[2]}`
    const payload = await verifyJwt(tamperedPayload, SECRET)
    expect(payload).toBeNull()
  })

  it('verifyJwt returns null for malformed input', async () => {
    expect(await verifyJwt('', SECRET)).toBeNull()
    expect(await verifyJwt('not-a-jwt', SECRET)).toBeNull()
    expect(await verifyJwt('two.parts', SECRET)).toBeNull()
    expect(await verifyJwt('a.b.c.d', SECRET)).toBeNull()
  })

  it('verifyJwt returns null for an expired token', async () => {
    // Manually construct an expired payload
    const expiredPayload: JwtPayload = {
      ...testPayload,
      iat: Math.floor(Date.now() / 1000) - 3600,
      exp: Math.floor(Date.now() / 1000) - 1, // expired 1 second ago
    }

    // We need to sign it manually to set custom iat/exp
    // Use the same signing logic: header.payload.signature
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '')
    const payload = btoa(JSON.stringify(expiredPayload))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '')
    const signingInput = `${header}.${payload}`

    const key = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(SECRET),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign'],
    )
    const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(signingInput))
    const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '')

    const expiredToken = `${signingInput}.${sigB64}`
    const result = await verifyJwt(expiredToken, SECRET)
    expect(result).toBeNull()
  })

  it('handles null picture field', async () => {
    const payloadWithNullPicture = { ...testPayload, picture: null }
    const token = await signJwt(payloadWithNullPicture, SECRET)
    const result = await verifyJwt(token, SECRET)

    expect(result).not.toBeNull()
    expect(result?.picture).toBeNull()
  })
})
