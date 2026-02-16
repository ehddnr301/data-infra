import { getColumns, getDataset, getDatasets } from '@/api/catalog'
import { useQuery } from '@tanstack/react-query'

export function useDatasets(params?: { domain?: string; page?: number; pageSize?: number }) {
  return useQuery({
    queryKey: ['catalog', 'datasets', params],
    queryFn: () => getDatasets(params),
  })
}

export function useDataset(id: string) {
  return useQuery({
    queryKey: ['catalog', 'dataset', id],
    queryFn: () => getDataset(id),
    enabled: Boolean(id),
  })
}

export function useColumns(datasetId: string) {
  return useQuery({
    queryKey: ['catalog', 'columns', datasetId],
    queryFn: () => getColumns(datasetId),
    enabled: Boolean(datasetId),
  })
}
