import type { Context } from 'hono'
import { ZodError } from 'zod'
import { AppError, internal, notFound, validationError } from '../lib/errors'

export function toProblemResponse(c: Context, error: AppError): Response {
  return new Response(JSON.stringify(error.toProblemDetail(c.req.url)), {
    status: error.status,
    headers: {
      'Content-Type': 'application/problem+json; charset=utf-8',
    },
  })
}

export function errorHandler(err: Error, c: Context): Response {
  if (err instanceof AppError) {
    return toProblemResponse(c, err)
  }

  if (err instanceof ZodError) {
    const detail = err.issues
      .map((issue) => `${issue.path.join('.') || 'root'}: ${issue.message}`)
      .join(', ')
    return toProblemResponse(c, validationError(detail))
  }

  const detail =
    c.env.ENVIRONMENT === 'prod' ? undefined : err.message || 'Unknown error'
  return toProblemResponse(c, internal(detail))
}

export function notFoundHandler(c: Context): Response {
  return toProblemResponse(c, notFound('Route does not exist'))
}
