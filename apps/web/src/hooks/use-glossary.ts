import {
  createGlossaryTerm,
  deleteGlossaryTerm,
  getGlossaryTerm,
  getGlossaryTerms,
  updateGlossaryTerm,
} from '@/api/glossary'
import { queryClient } from '@/lib/query-client'
import { useMutation, useQuery } from '@tanstack/react-query'

export function useGlossaryTerms(params?: {
  domain?: string
  q?: string
  page?: number
  pageSize?: number
}) {
  return useQuery({
    queryKey: ['catalog', 'glossary', 'list', params],
    queryFn: () => getGlossaryTerms(params),
  })
}

export function useGlossaryTerm(id: string) {
  return useQuery({
    queryKey: ['catalog', 'glossary', 'detail', id],
    queryFn: () => getGlossaryTerm(id),
    enabled: Boolean(id),
  })
}

export function useCreateGlossaryTerm() {
  return useMutation({
    mutationFn: createGlossaryTerm,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['catalog', 'glossary', 'list'] })
    },
  })
}

export function useUpdateGlossaryTerm() {
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string
      input: {
        term?: string
        definition?: string
        related_terms?: string[]
      }
    }) => updateGlossaryTerm(id, input),
    onSuccess: (_result, variables) => {
      void queryClient.invalidateQueries({ queryKey: ['catalog', 'glossary', 'list'] })
      void queryClient.invalidateQueries({
        queryKey: ['catalog', 'glossary', 'detail', variables.id],
      })
    },
  })
}

export function useDeleteGlossaryTerm() {
  return useMutation({
    mutationFn: deleteGlossaryTerm,
    onSuccess: (_result, id) => {
      void queryClient.invalidateQueries({ queryKey: ['catalog', 'glossary', 'list'] })
      void queryClient.invalidateQueries({ queryKey: ['catalog', 'glossary', 'detail', id] })
    },
  })
}
