export type ApiSuccess<T> = {
  success: true
  data: T
  meta?: Record<string, unknown>
}

export type ApiFailure = {
  success: false
  error: string
  code?: string
}

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure

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
