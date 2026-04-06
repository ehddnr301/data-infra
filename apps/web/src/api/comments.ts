import { apiDelete, apiGet, apiPost, apiPut } from '@/lib/api-client'
import type {
  ApiSuccess,
  CommentCategory,
  CommentSource,
  DatasetComment,
  PaginatedResponse,
} from '@pseudolab/shared-types'

export function getComments(
  datasetId: string,
  params?: {
    category?: CommentCategory
    source?: CommentSource
    page?: number
    pageSize?: number
  },
) {
  return apiGet<PaginatedResponse<DatasetComment>>(`/datasets/${datasetId}/comments`, { params })
}

export function createComment(
  datasetId: string,
  input: { category: CommentCategory; content: string; source?: CommentSource },
) {
  return apiPost<ApiSuccess<DatasetComment>>(`/datasets/${datasetId}/comments`, input)
}

export function updateComment(datasetId: string, commentId: string, input: { content: string }) {
  return apiPut<ApiSuccess<DatasetComment>>(`/datasets/${datasetId}/comments/${commentId}`, input)
}

export function deleteComment(datasetId: string, commentId: string) {
  return apiDelete<ApiSuccess<{ deleted: true }>>(`/datasets/${datasetId}/comments/${commentId}`)
}
