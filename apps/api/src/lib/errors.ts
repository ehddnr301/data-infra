import type { ProblemDetail } from '@pseudolab/shared-types'

export class AppError extends Error {
  constructor(
    public status: number,
    public title: string,
    public type = '/errors/internal',
    public detail?: string,
  ) {
    super(title)
  }

  toProblemDetail(instance?: string): ProblemDetail {
    return {
      type: this.type,
      title: this.title,
      status: this.status,
      ...(this.detail ? { detail: this.detail } : {}),
      ...(instance ? { instance } : {}),
    }
  }
}

export function badRequest(detail?: string): AppError {
  return new AppError(400, 'Bad Request', '/errors/bad-request', detail)
}

export function notFound(detail?: string): AppError {
  return new AppError(404, 'Not Found', '/errors/not-found', detail)
}

export function validationError(detail?: string): AppError {
  return new AppError(400, 'Validation Error', '/errors/validation', detail)
}

export function internal(detail?: string): AppError {
  return new AppError(500, 'Internal Server Error', '/errors/internal', detail)
}
