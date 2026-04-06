import { createComment, deleteComment, getComments, updateComment } from '@/api/comments'
import { queryClient } from '@/lib/query-client'
import type { CommentCategory, CommentSource } from '@pseudolab/shared-types'
import { useMutation, useQuery } from '@tanstack/react-query'

export function useComments(
  datasetId: string,
  params?: {
    category?: CommentCategory
    source?: CommentSource
    page?: number
    pageSize?: number
  },
) {
  return useQuery({
    queryKey: ['comments', datasetId, params],
    queryFn: () => getComments(datasetId, params),
    enabled: Boolean(datasetId),
  })
}

export function useCreateComment() {
  return useMutation({
    mutationFn: ({
      datasetId,
      input,
    }: {
      datasetId: string
      input: { category: CommentCategory; content: string; source?: CommentSource }
    }) => createComment(datasetId, input),
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['comments', variables.datasetId] })
    },
  })
}

export function useUpdateComment() {
  return useMutation({
    mutationFn: ({
      datasetId,
      commentId,
      input,
    }: {
      datasetId: string
      commentId: string
      input: { content: string }
    }) => updateComment(datasetId, commentId, input),
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['comments', variables.datasetId] })
    },
  })
}

export function useDeleteComment() {
  return useMutation({
    mutationFn: ({
      datasetId,
      commentId,
    }: {
      datasetId: string
      commentId: string
    }) => deleteComment(datasetId, commentId),
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['comments', variables.datasetId] })
    },
  })
}
