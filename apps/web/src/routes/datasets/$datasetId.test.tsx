import { DatasetDetailPage } from '@/routes/datasets/$datasetId'
import { fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { Mock } from 'vitest'

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <a href="/">{children}</a>,
  useNavigate: () => vi.fn(),
  useParams: () => ({ datasetId: 'discord.messages.v1' }),
}))

vi.mock('@/components/lineage/lineage-viewer', () => ({
  LineageViewer: () => <div>lineage-viewer</div>,
}))

vi.mock('@/hooks/use-catalog', () => ({
  useDataset: vi.fn(),
  useColumns: vi.fn(),
  useDatasetPreview: vi.fn(),
}))

vi.mock('@/hooks/use-lineage', () => ({
  useLineage: vi.fn(),
  useSaveLineage: vi.fn(),
}))

import { useColumns, useDataset, useDatasetPreview } from '@/hooks/use-catalog'
import { useLineage, useSaveLineage } from '@/hooks/use-lineage'

const baseDatasetQuery = {
  isPending: false,
  isError: false,
  data: {
    data: {
      id: 'discord.messages.v1',
      domain: 'discord',
      name: 'Discord Messages',
      description: 'Dataset for preview tests',
      schema_json: null,
      lineage_json: null,
      owner: 'qa',
      tags: '["discord"]',
      created_at: '2025-01-01T00:00:00.000Z',
      updated_at: '2025-01-01T00:00:00.000Z',
    },
  },
  refetch: vi.fn(),
}

const baseColumnsQuery = {
  isPending: false,
  isError: false,
  data: {
    data: [],
  },
  refetch: vi.fn(),
}

const baseLineageQuery = {
  isPending: false,
  isError: false,
  data: {
    data: {
      version: 1 as const,
      nodes: [],
      edges: [],
    },
  },
  refetch: vi.fn(),
}

const baseSaveLineageMutation = {
  mutateAsync: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
}

describe('DatasetDetailPage preview tab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useDataset as Mock).mockReturnValue(baseDatasetQuery)
    ;(useColumns as Mock).mockReturnValue(baseColumnsQuery)
    ;(useLineage as Mock).mockReturnValue(baseLineageQuery)
    ;(useSaveLineage as Mock).mockReturnValue(baseSaveLineageMutation)
  })

  it('enables preview fetch only when preview tab is active', () => {
    ;(useDatasetPreview as Mock).mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        data: {
          datasetId: 'discord.messages.v1',
          source: { kind: 'mapped-table', table: 'discord_messages' },
          columns: ['id', 'content'],
          rows: [{ id: 2, content: 'row-two' }],
          meta: { limit: 20, returned: 1 },
        },
      },
      refetch: vi.fn(),
    })

    render(<DatasetDetailPage />)

    expect(useDatasetPreview).toHaveBeenCalledWith(
      'discord.messages.v1',
      expect.objectContaining({ limit: 20, enabled: false }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))

    expect(useDatasetPreview).toHaveBeenLastCalledWith(
      'discord.messages.v1',
      expect.objectContaining({ limit: 20, enabled: true }),
    )
  })

  it('updates preview limit selector and hint text', () => {
    ;(useDatasetPreview as Mock).mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        data: {
          datasetId: 'discord.messages.v1',
          source: { kind: 'mapped-table', table: 'discord_messages' },
          columns: ['id', 'content'],
          rows: [{ id: 2, content: 'row-two' }],
          meta: { limit: 20, returned: 1 },
        },
      },
      refetch: vi.fn(),
    })

    render(<DatasetDetailPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))

    expect(screen.getByText('최신 20건 기준 정렬')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('프리뷰 행 수'), {
      target: { value: '50' },
    })

    expect(useDatasetPreview).toHaveBeenLastCalledWith(
      'discord.messages.v1',
      expect.objectContaining({ limit: 50, enabled: true }),
    )
    expect(screen.getByText('최신 50건 기준 정렬')).toBeInTheDocument()
  })

  it('supports client-side sorting and JSON expand collapse', () => {
    ;(useDatasetPreview as Mock).mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        data: {
          datasetId: 'discord.messages.v1',
          source: { kind: 'mapped-table', table: 'discord_messages' },
          columns: ['id', 'content', 'payload'],
          rows: [
            { id: 2, content: 'row-two', payload: { nested: true } },
            { id: 1, content: 'row-one', payload: { nested: false } },
          ],
          meta: { limit: 20, returned: 2 },
        },
      },
      refetch: vi.fn(),
    })

    render(<DatasetDetailPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))

    const beforeSortRows = screen.getAllByRole('row')
    expect(beforeSortRows[1]?.textContent).toContain('row-two')

    fireEvent.click(screen.getByRole('button', { name: 'id' }))

    const afterSortRows = screen.getAllByRole('row')
    expect(afterSortRows[1]?.textContent).toContain('row-one')

    const expandButtons = screen.getAllByRole('button', { name: '펼치기' })
    expect(expandButtons.length).toBeGreaterThan(0)
    const firstExpandButton = expandButtons[0]
    if (!firstExpandButton) {
      throw new Error('expand button not found')
    }
    fireEvent.click(firstExpandButton)
    expect(screen.getAllByRole('button', { name: '접기' }).length).toBeGreaterThan(0)
    expect(screen.getByText(/"nested": false/)).toBeInTheDocument()
  })

  it('shows unmapped empty state when preview source is not mapped', () => {
    ;(useDatasetPreview as Mock).mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        data: {
          datasetId: 'discord.messages.v1',
          source: { kind: 'unmapped', table: null },
          columns: [],
          rows: [],
          meta: { limit: 20, returned: 0, reason: 'dataset-not-mapped' },
        },
      },
      refetch: vi.fn(),
    })

    render(<DatasetDetailPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))

    expect(screen.getByText('프리뷰 준비중')).toBeInTheDocument()
  })
})
