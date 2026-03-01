import { getLineage, putLineage } from '@/api/lineage'
import { useLineage, useSaveLineage } from '@/hooks/use-lineage'
import { queryClient } from '@/lib/query-client'
import type { LineageGraph } from '@pseudolab/shared-types'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

vi.mock('@/api/lineage', () => ({
  getLineage: vi.fn(),
  putLineage: vi.fn(),
}))

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

const sampleGraph: LineageGraph = {
  version: 1,
  nodes: [
    {
      id: 'ds.github.repo.v1',
      type: 'dataset',
      position: { x: 0, y: 0 },
      data: { datasetId: 'ds.github.repo.v1', label: 'Repo', domain: 'github' },
    },
  ],
  edges: [],
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

it('useLineage queries lineage graph by dataset id', async () => {
  vi.mocked(getLineage).mockResolvedValue({ success: true, data: sampleGraph })

  const { result } = renderHook(() => useLineage('ds.github.repo.v1'), {
    wrapper: createWrapper(),
  })

  await waitFor(() => {
    expect(result.current.isSuccess).toBe(true)
  })

  expect(getLineage).toHaveBeenCalledWith('ds.github.repo.v1')
  expect(result.current.data?.data).toEqual(sampleGraph)
})

it('useSaveLineage saves graph and invalidates lineage query key', async () => {
  vi.mocked(putLineage).mockResolvedValue({ success: true, data: sampleGraph })
  const invalidateSpy = vi
    .spyOn(queryClient, 'invalidateQueries')
    .mockResolvedValue(undefined as never)

  const { result } = renderHook(() => useSaveLineage('ds.github.repo.v1'), {
    wrapper: createWrapper(),
  })

  await act(async () => {
    await result.current.mutateAsync(sampleGraph)
  })

  expect(putLineage).toHaveBeenCalledWith('ds.github.repo.v1', sampleGraph)
  expect(invalidateSpy).toHaveBeenCalledWith({
    queryKey: ['catalog', 'lineage', 'ds.github.repo.v1'],
  })
})
