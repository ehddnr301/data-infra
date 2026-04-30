import {
  type ListDiscussionsParams,
  getDiscussion,
  getDiscussionComments,
  getDiscussions,
} from '@/api/discussions'
import { useQuery } from '@tanstack/react-query'

export function useDiscussions(params?: ListDiscussionsParams) {
  return useQuery({
    queryKey: ['discussions', 'list', params],
    queryFn: () => getDiscussions(params),
  })
}

export function useDiscussion(id: string) {
  return useQuery({
    queryKey: ['discussions', 'detail', id],
    queryFn: () => getDiscussion(id),
    enabled: Boolean(id),
  })
}

export function useDiscussionComments(id: string) {
  return useQuery({
    queryKey: ['discussions', 'comments', id],
    queryFn: () => getDiscussionComments(id),
    enabled: Boolean(id),
  })
}
