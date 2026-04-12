import type { Env } from '@pseudolab/shared-types'
import type { Context, Next } from 'hono'
import { AppError } from '../lib/errors'
import { type JwtPayload, verifyJwt } from '../lib/jwt'
import { extractBearerToken } from './internal-auth'

export type AuthUser = { email: string; name: string; role?: string }
export type AuthEnv = { Bindings: Env; Variables: { user: AuthUser } }

export async function requireUserAuth(c: Context<AuthEnv>, next: Next) {
  const token = extractBearerToken(c.req.header('Authorization'))
  if (!token) {
    throw new AppError(401, 'Unauthorized', '/errors/unauthorized', 'Missing bearer token')
  }

  // Path 1: JWT token (contains dots)
  if (token.includes('.')) {
    const jwtSecret = c.env.JWT_SECRET?.trim()
    if (!jwtSecret) {
      throw new AppError(
        503,
        'Service Unavailable',
        '/errors/service-unavailable',
        'JWT_SECRET is not configured',
      )
    }

    const payload: JwtPayload | null = await verifyJwt(token, jwtSecret)
    if (!payload) {
      throw new AppError(401, 'Unauthorized', '/errors/unauthorized', 'Invalid or expired token')
    }

    // Check current role in D1 (may have changed since JWT was issued)
    const user = await c.env.DB.prepare('SELECT role FROM users WHERE email = ?')
      .bind(payload.email)
      .first<{ role: string }>()

    if (!user) {
      throw new AppError(401, 'Unauthorized', '/errors/unauthorized', 'User not found')
    }

    if (user.role === 'pending') {
      throw new AppError(403, 'Forbidden', '/errors/forbidden', '승인 대기 중입니다')
    }

    c.set('user', { email: payload.email, name: payload.name, role: user.role })
    return next()
  }

  // Path 2: Internal service token (no dots)
  const expectedToken = c.env.INTERNAL_API_TOKEN?.trim()
  if (!expectedToken) {
    throw new AppError(
      503,
      'Service Unavailable',
      '/errors/service-unavailable',
      'INTERNAL_API_TOKEN is not configured',
    )
  }

  if (token !== expectedToken) {
    throw new AppError(401, 'Unauthorized', '/errors/unauthorized', 'Invalid bearer token')
  }

  const email = c.req.header('X-User-Email')?.trim()
  if (!email) {
    throw new AppError(400, 'Bad Request', '/errors/bad-request', 'X-User-Email header is required')
  }

  const rawName = c.req.header('X-User-Name')?.trim() ?? ''
  const name = decodeURIComponent(rawName)

  c.set('user', { email, name, role: 'admin' })
  return next()
}
