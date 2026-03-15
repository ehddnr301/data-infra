import { apiGet } from '@/lib/api-client'
import type {
  ApiSuccess,
  CatalogColumn,
  CatalogDataset,
  DatasetPreviewResponse,
  PaginatedResponse,
} from '@pseudolab/shared-types'

const CATALOG_DATASET_BASE = ['/catalog', 'datasets'].join('/')

export function getDatasets(params?: {
  domain?: string
  page?: number
  pageSize?: number
}) {
  return apiGet<PaginatedResponse<CatalogDataset>>(CATALOG_DATASET_BASE, { params })
}

export function getDataset(id: string) {
  return apiGet<ApiSuccess<CatalogDataset>>(`${CATALOG_DATASET_BASE}/${id}`)
}

export function getColumns(datasetId: string) {
  return apiGet<ApiSuccess<CatalogColumn[]>>(`${CATALOG_DATASET_BASE}/${datasetId}/columns`)
}

export function getDatasetPreview(datasetId: string, params?: { limit?: number }) {
  return apiGet<ApiSuccess<DatasetPreviewResponse>>(
    `${CATALOG_DATASET_BASE}/${datasetId}/preview`,
    {
      params,
    },
  )
}
