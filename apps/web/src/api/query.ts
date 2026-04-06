import { apiGet, apiPost } from '@/lib/api-client'
import type { ApiSuccess, PaginatedResponse, QueryHistoryEntry } from '@pseudolab/shared-types'

type QueryResult = {
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  truncated: boolean
  executed_sql: string
}

type QueryResponse = ApiSuccess<QueryResult> & {
  meta: { execution_ms: number }
}

export function executeQuery(sql: string) {
  return apiPost<QueryResponse>('/query', { sql })
}

export function getQueryHistory(params?: {
  user?: string
  page?: number
  pageSize?: number
}) {
  return apiGet<PaginatedResponse<QueryHistoryEntry>>('/query/history', { params })
}

export function getQueryHistoryEntry(id: string) {
  return apiGet<ApiSuccess<QueryHistoryEntry>>(`/query/history/${id}`)
}
