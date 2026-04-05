import type { Env } from '@pseudolab/shared-types'
import type { Context, Next } from 'hono'
import { AppError } from '../lib/errors'
import { extractBearerToken } from './internal-auth'

export type AuthUser = { email: string; name: string }
export type AuthEnv = { Bindings: Env; Variables: { user: AuthUser } }

export async function requireUserAuth(c: Context<AuthEnv>, next: Next) {
  const expectedToken = c.env.INTERNAL_API_TOKEN?.trim()
  if (!expectedToken) {
    throw new AppError(
      503,
      'Service Unavailable',
      '/errors/service-unavailable',
      'INTERNAL_API_TOKEN is not configured',
    )
  }

  const providedToken = extractBearerToken(c.req.header('Authorization'))
  if (!providedToken || providedToken !== expectedToken) {
    throw new AppError(
      401,
      'Unauthorized',
      '/errors/unauthorized',
      'Missing or invalid bearer token',
    )
  }

  const email = c.req.header('X-User-Email')?.trim()
  if (!email) {
    throw new AppError(400, 'Bad Request', '/errors/bad-request', 'X-User-Email header is required')
  }

  const name = c.req.header('X-User-Name')?.trim() ?? ''

  c.set('user', { email, name })
  await next()
}
