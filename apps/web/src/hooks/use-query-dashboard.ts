import { getManifest } from '@/api/manifest'
import { executeQuery, getQueryHistory } from '@/api/query'
import { queryClient } from '@/lib/query-client'
import { useMutation, useQuery } from '@tanstack/react-query'

export function useExecuteQuery() {
  return useMutation({
    mutationFn: (sql: string) => executeQuery(sql),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['query', 'history'] })
    },
  })
}

export function useQueryHistory(params?: {
  user?: string
  page?: number
  pageSize?: number
}) {
  return useQuery({
    queryKey: ['query', 'history', params],
    queryFn: () => getQueryHistory(params),
  })
}

export function useManifest() {
  return useQuery({
    queryKey: ['ai', 'manifest'],
    queryFn: () => getManifest(),
    staleTime: 5 * 60 * 1000,
  })
}
