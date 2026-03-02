import type { Env } from '@pseudolab/shared-types'
import type { Context, Next } from 'hono'
import { AppError } from '../lib/errors'

const BEARER_PREFIX = 'Bearer '

function extractBearerToken(authorization: string | undefined): string | null {
  if (!authorization || !authorization.startsWith(BEARER_PREFIX)) {
    return null
  }

  const token = authorization.slice(BEARER_PREFIX.length).trim()
  return token.length > 0 ? token : null
}

export async function requireInternalBearer(c: Context<{ Bindings: Env }>, next: Next) {
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

  await next()
}
