import { apiGet } from '@/lib/api-client'
import type {
  ApiSuccess,
  CatalogColumn,
  CatalogDataset,
  DatasetPreviewResponse,
  PaginatedResponse,
} from '@pseudolab/shared-types'

export function getDatasets(params?: {
  domain?: string
  page?: number
  pageSize?: number
}) {
  return apiGet<PaginatedResponse<CatalogDataset>>('/catalog/datasets', { params })
}

export function getDataset(id: string) {
  return apiGet<ApiSuccess<CatalogDataset>>(`/catalog/datasets/${id}`)
}

export function getColumns(datasetId: string) {
  return apiGet<ApiSuccess<CatalogColumn[]>>(`/catalog/datasets/${datasetId}/columns`)
}

export function getDatasetPreview(datasetId: string, params?: { limit?: number }) {
  return apiGet<ApiSuccess<DatasetPreviewResponse>>(`/catalog/datasets/${datasetId}/preview`, {
    params,
  })
}
