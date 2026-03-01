import { apiGet, apiPut } from '@/lib/api-client'
import type { ApiSuccess, LineageGraph } from '@pseudolab/shared-types'

export function getLineage(datasetId: string) {
  return apiGet<ApiSuccess<LineageGraph>>(`/catalog/lineage/${datasetId}`)
}

export function putLineage(datasetId: string, graph: LineageGraph) {
  return apiPut<ApiSuccess<LineageGraph>>(`/catalog/lineage/${datasetId}`, graph)
}
