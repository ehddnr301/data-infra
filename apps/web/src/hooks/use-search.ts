import { getIntegratedSearch } from '@/api/search'
import type { DomainName, SearchType } from '@pseudolab/shared-types'
import { useQuery } from '@tanstack/react-query'

export function useIntegratedSearch(params: {
  q: string
  type: SearchType
  domain?: DomainName
  page: number
  pageSize: number
}) {
  return useQuery({
    queryKey: ['catalog', 'search', params],
    queryFn: () =>
      getIntegratedSearch({
        q: params.q,
        type: params.type,
        domain: params.domain,
        page: params.page,
        pageSize: params.pageSize,
      }),
    enabled: params.q.trim().length > 0,
  })
}
