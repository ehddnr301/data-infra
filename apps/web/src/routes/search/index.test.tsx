import { SearchPage } from '@/routes/search'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { Mock } from 'vitest'

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children, className }: { children: ReactNode; className?: string }) => (
    <a className={className} href="/">
      {children}
    </a>
  ),
}))

vi.mock('@/hooks/use-search', () => ({
  useIntegratedSearch: vi.fn(),
}))

vi.mock('@/hooks/use-recent-searches', () => ({
  useRecentSearches: vi.fn(() => ({
    recentSearches: ['recent-term'],
    addRecentSearch: vi.fn(),
    removeRecentSearch: vi.fn(),
    clearRecentSearches: vi.fn(),
  })),
}))

import { useIntegratedSearch } from '@/hooks/use-search'

describe('SearchPage', () => {
  it('renders empty state when query is missing', () => {
    window.history.pushState({}, '', '/search')
    ;(useIntegratedSearch as Mock).mockReturnValue({
      isPending: false,
      isError: false,
      data: undefined,
      refetch: vi.fn(),
    })

    render(<SearchPage />)
    expect(screen.getByText('검색어를 입력하세요.')).toBeInTheDocument()
  })

  it('renders grouped results in all mode', () => {
    window.history.pushState({}, '', '/search?q=alpha&type=all')
    ;(useIntegratedSearch as Mock).mockReturnValue({
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
      data: {
        success: true,
        data: {
          query: 'alpha',
          type: 'all',
          groups: {
            datasets: {
              total: 1,
              items: [
                {
                  id: 'ds-1',
                  domain: 'github',
                  name: 'alpha dataset',
                  description: 'description',
                  updated_at: '2025-01-01T00:00:00.000Z',
                },
              ],
            },
            columns: {
              total: 1,
              items: [
                {
                  dataset_id: 'ds-1',
                  dataset_name: 'alpha dataset',
                  domain: 'github',
                  column_name: 'alpha_column',
                  data_type: 'TEXT',
                  description: 'column description',
                  is_pii: false,
                },
              ],
            },
            glossary: {
              total: 1,
              items: [
                {
                  id: 'term-1',
                  domain: 'github',
                  term: 'alpha term',
                  definition: 'alpha definition',
                  updated_at: '2025-01-01T00:00:00.000Z',
                },
              ],
            },
          },
        },
        meta: {
          cache: 'miss',
          tookMs: 1,
        },
      },
    })

    render(<SearchPage />)

    expect(screen.getByText('datasets (1)')).toBeInTheDocument()
    expect(screen.getByText('columns (1)')).toBeInTheDocument()
    expect(screen.getByText('glossary (1)')).toBeInTheDocument()
    expect(screen.getByText('description')).toBeInTheDocument()
  })
})
