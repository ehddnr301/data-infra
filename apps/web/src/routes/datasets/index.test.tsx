import { DatasetsPage } from '@/routes/datasets'
import { fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { Mock } from 'vitest'

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <a href="/">{children}</a>,
}))

vi.mock('@/hooks/use-catalog', () => ({
  useDatasets: vi.fn(),
}))

import { useDatasets } from '@/hooks/use-catalog'

const baseResult = {
  isPending: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
}

describe('DatasetsPage domain filter behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders non-empty discord results', () => {
    ;(useDatasets as Mock).mockImplementation((params?: { domain?: string }) => {
      if (params?.domain === 'discord') {
        return {
          ...baseResult,
          data: {
            data: [
              {
                id: 'discord.messages.v1',
                domain: 'discord',
                name: 'Discord Messages',
                description: 'Discord dataset',
                schema_json: null,
                lineage_json: null,
                owner: 'qa',
                tags: null,
                created_at: '2025-01-01T00:00:00.000Z',
                updated_at: '2025-01-01T00:00:00.000Z',
              },
            ],
          },
        }
      }

      return {
        ...baseResult,
        data: {
          data: [
            {
              id: 'github.events.v1',
              domain: 'github',
              name: 'GitHub Events',
              description: 'GitHub dataset',
              schema_json: null,
              lineage_json: null,
              owner: 'qa',
              tags: null,
              created_at: '2025-01-01T00:00:00.000Z',
              updated_at: '2025-01-01T00:00:00.000Z',
            },
          ],
        },
      }
    })

    render(<DatasetsPage />)
    fireEvent.click(screen.getByRole('button', { name: 'discord' }))

    expect(screen.getByText('Discord Messages')).toBeInTheDocument()
    expect(screen.queryByText('데이터셋이 없습니다.')).not.toBeInTheDocument()
  })

  it('renders empty state when discord results are empty', () => {
    ;(useDatasets as Mock).mockImplementation((params?: { domain?: string }) => {
      if (params?.domain === 'discord') {
        return {
          ...baseResult,
          data: { data: [] },
        }
      }

      return {
        ...baseResult,
        data: {
          data: [
            {
              id: 'github.events.v1',
              domain: 'github',
              name: 'GitHub Events',
              description: 'GitHub dataset',
              schema_json: null,
              lineage_json: null,
              owner: 'qa',
              tags: null,
              created_at: '2025-01-01T00:00:00.000Z',
              updated_at: '2025-01-01T00:00:00.000Z',
            },
          ],
        },
      }
    })

    render(<DatasetsPage />)
    fireEvent.click(screen.getByRole('button', { name: 'discord' }))

    expect(screen.getByText('데이터셋이 없습니다.')).toBeInTheDocument()
  })

  it('calls useDatasets with discord domain when discord filter is clicked', () => {
    ;(useDatasets as Mock).mockReturnValue({
      ...baseResult,
      data: { data: [] },
    })

    render(<DatasetsPage />)

    expect(useDatasets).toHaveBeenCalledWith({
      domain: undefined,
      page: 1,
      pageSize: 20,
    })

    fireEvent.click(screen.getByRole('button', { name: 'discord' }))

    expect(useDatasets).toHaveBeenLastCalledWith({
      domain: 'discord',
      page: 1,
      pageSize: 20,
    })
  })
})
