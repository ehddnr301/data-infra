import { ListingsPage } from '@/routes/listings'
import { fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { Mock } from 'vitest'

const CATALOG_API_BASE = ['/api/catalog', 'datasets'].join('/')

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <a href="/">{children}</a>,
}))

vi.mock('@/hooks/use-marketplace', () => ({
  useListings: vi.fn(),
}))

import { useListings } from '@/hooks/use-marketplace'

const baseQuery = {
  isPending: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
}

describe('ListingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useListings as Mock).mockReturnValue({
      ...baseQuery,
      data: {
        data: [
          {
            id: 'listing-discord-messages',
            dataset_id: 'discord.messages.v1',
            domain: 'discord',
            slug: 'messages.v1',
            title: 'Discord Messages',
            subtitle: 'Discord dataset product',
            description: 'Moderation triage and engagement review',
            category: 'community',
            update_frequency: 'internal',
            coverage_summary: 'Community messages dataset',
            documentation_url: `${CATALOG_API_BASE}/discord.messages.v1`,
            last_verified_at: '2025-01-10T00:00:00.000Z',
            owner: {
              id: 'owner-discord',
              slug: 'discord-marketplace',
              display_name: 'Discord Data Team',
              team_name: 'Data Platform',
              role_title: 'Owner',
              bio: null,
              avatar_url: null,
              contact_email: 'discord@pseudolab.org',
              slack_channel: '#discord-data',
            },
            business_need_tags: ['Moderation triage'],
            preview_available: true,
            has_pii: true,
          },
          {
            id: 'listing-github-push-events',
            dataset_id: 'github.push-events.v1',
            domain: 'github',
            slug: 'push-events.v1',
            title: 'Push Events',
            subtitle: 'GitHub dataset product',
            description: 'Release and throughput monitoring',
            category: 'engineering',
            update_frequency: 'internal',
            coverage_summary: 'Repository push activity dataset',
            documentation_url: `${CATALOG_API_BASE}/github.push-events.v1`,
            last_verified_at: '2025-01-08T00:00:00.000Z',
            owner: {
              id: 'owner-github',
              slug: 'github-marketplace',
              display_name: 'GitHub Data Team',
              team_name: 'Data Platform',
              role_title: 'Owner',
              bio: null,
              avatar_url: null,
              contact_email: 'github@pseudolab.org',
              slack_channel: '#github-data',
            },
            business_need_tags: ['Release monitoring'],
            preview_available: true,
            has_pii: false,
          },
        ],
      },
    })
  })

  it('renders listing cards', () => {
    render(<ListingsPage />)

    expect(screen.getByText('Discord Messages')).toBeInTheDocument()
    expect(screen.getByText('Push Events')).toBeInTheDocument()
  })

  it('filters by category', () => {
    render(<ListingsPage />)

    fireEvent.change(screen.getByLabelText('카테고리 필터'), {
      target: { value: 'engineering' },
    })

    expect(screen.queryByText('Discord Messages')).not.toBeInTheDocument()
    expect(screen.getByText('Push Events')).toBeInTheDocument()
  })

  it('sorts by name', () => {
    render(<ListingsPage />)

    fireEvent.change(screen.getByLabelText('정렬'), {
      target: { value: 'name' },
    })

    const cards = screen.getAllByTestId('listing-card')
    expect(cards[0]?.textContent).toContain('Discord Messages')
    expect(cards[1]?.textContent).toContain('Push Events')
  })
})
