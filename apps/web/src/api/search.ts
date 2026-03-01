import { apiGet } from '@/lib/api-client'
import type {
  ApiSuccess,
  DomainName,
  IntegratedSearchResult,
  SearchType,
} from '@pseudolab/shared-types'

export function getIntegratedSearch(params: {
  q: string
  type?: SearchType
  domain?: DomainName
  page?: number
  pageSize?: number
}) {
  return apiGet<ApiSuccess<IntegratedSearchResult>>('/search', { params })
}
