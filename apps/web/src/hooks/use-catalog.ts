import { getColumns, getDataset, getDatasetPreview, getDatasets } from '@/api/catalog'
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

export function useDatasetPreview(
  datasetId: string,
  options?: { limit?: number; enabled?: boolean },
) {
  const limit = options?.limit ?? 20

  return useQuery({
    queryKey: ['catalog', 'preview', datasetId, { limit }],
    queryFn: () => getDatasetPreview(datasetId, { limit }),
    enabled: Boolean(datasetId) && (options?.enabled ?? true),
  })
}
