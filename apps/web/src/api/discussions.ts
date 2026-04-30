import { apiGet, apiPost } from '@/lib/api-client'
import type {
  ApiSuccess,
  CreateDiscussionCommentInput,
  CreateDiscussionInput,
  DiscussionComment,
  DiscussionPost,
  DiscussionPostSummary,
  DiscussionUpvoteResponse,
  PaginatedResponse,
} from '@pseudolab/shared-types'

export type ListDiscussionsParams = {
  page?: number
  pageSize?: number
  sort?: 'popular' | 'latest'
  dataset_id?: string
  listing_id?: string
  query_history_id?: string
}

export function getDiscussions(params?: ListDiscussionsParams) {
  return apiGet<PaginatedResponse<DiscussionPostSummary>>('/discussions', { params })
}

export function getDiscussion(id: string) {
  return apiGet<ApiSuccess<DiscussionPost>>(`/discussions/${id}`)
}

export function getDiscussionComments(id: string) {
  return apiGet<ApiSuccess<DiscussionComment[]>>(`/discussions/${id}/comments`)
}

export function createDiscussion(input: CreateDiscussionInput) {
  return apiPost<ApiSuccess<DiscussionPost>>('/discussions', input as Record<string, unknown>)
}

export function createDiscussionComment(id: string, input: CreateDiscussionCommentInput) {
  return apiPost<ApiSuccess<DiscussionComment>>(
    `/discussions/${id}/comments`,
    input as Record<string, unknown>,
  )
}

export function upvoteDiscussion(id: string) {
  return apiPost<ApiSuccess<DiscussionUpvoteResponse>>(`/discussions/${id}/upvote`, {})
}

export function upvoteDiscussionComment(id: string, commentId: string) {
  return apiPost<ApiSuccess<DiscussionUpvoteResponse>>(
    `/discussions/${id}/comments/${commentId}/upvote`,
    {},
  )
}
