import { getLineage, putLineage } from '@/api/lineage'
import { queryClient } from '@/lib/query-client'
import type { LineageGraph } from '@pseudolab/shared-types'
import { useMutation, useQuery } from '@tanstack/react-query'

export function useLineage(datasetId: string) {
  return useQuery({
    queryKey: ['catalog', 'lineage', datasetId],
    queryFn: () => getLineage(datasetId),
    enabled: Boolean(datasetId),
  })
}

export function useSaveLineage(datasetId: string) {
  return useMutation({
    mutationFn: (graph: LineageGraph) => putLineage(datasetId, graph),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['catalog', 'lineage', datasetId] })
    },
  })
}
