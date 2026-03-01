import { apiDelete, apiGet, apiPost, apiPut } from '@/lib/api-client'
import type { ApiSuccess, GlossaryTerm, PaginatedResponse } from '@pseudolab/shared-types'

export function getGlossaryTerms(params?: {
  domain?: string
  q?: string
  page?: number
  pageSize?: number
}) {
  return apiGet<PaginatedResponse<GlossaryTerm>>('/catalog/glossary', { params })
}

export function getGlossaryTerm(id: string) {
  return apiGet<ApiSuccess<GlossaryTerm>>(`/catalog/glossary/${id}`)
}

export function createGlossaryTerm(input: {
  domain: GlossaryTerm['domain']
  term: string
  definition: string
  related_terms?: string[]
}) {
  return apiPost<ApiSuccess<GlossaryTerm>>('/catalog/glossary', input)
}

export function updateGlossaryTerm(
  id: string,
  input: {
    term?: string
    definition?: string
    related_terms?: string[]
  },
) {
  return apiPut<ApiSuccess<GlossaryTerm>>(`/catalog/glossary/${id}`, input)
}

export function deleteGlossaryTerm(id: string) {
  return apiDelete<ApiSuccess<{ id: string; deleted: true }>>(`/catalog/glossary/${id}`)
}
