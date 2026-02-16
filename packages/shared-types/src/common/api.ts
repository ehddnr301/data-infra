export type ApiSuccess<T> = {
  success: true
  data: T
  meta?: Record<string, unknown>
}

export type ProblemDetail = {
  type: string
  title: string
  status: number
  detail?: string
  instance?: string
}

/** @deprecated RFC 7807 ProblemDetail을 사용하세요. 다음 메이저 버전에서 제거 예정. */
export type ApiFailure = {
  success: false
  error: string
  code?: string
}

export type ApiResponse<T> = ApiSuccess<T> | ProblemDetail

export type PaginatedResponse<T> = {
  success: true
  data: T[]
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
}
