import { DomainDetailPage } from '@/routes/domains/$domainKey'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { Mock } from 'vitest'

const CATALOG_API_BASE = ['/api/catalog', 'datasets'].join('/')

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <a href="/">{children}</a>,
  useParams: () => ({ domainKey: 'github' }),
}))

vi.mock('@/hooks/use-marketplace', () => ({
  useMarketplaceDomain: vi.fn(),
}))

import { useMarketplaceDomain } from '@/hooks/use-marketplace'

describe('DomainDetailPage', () => {
  it('renders domain hub listings', () => {
    ;(useMarketplaceDomain as Mock).mockReturnValue({
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
      data: {
        data: {
          key: 'github',
          label: 'GitHub',
          description: 'Repository datasets.',
          listing_count: 2,
          featured_listing_slug: 'push-events.v1',
          featured_listing_title: 'dl_push_events',
          listings: [
            {
              id: 'listing-github-push-events',
              dataset_id: 'github.push-events.v1',
              domain: 'github',
              slug: 'push-events.v1',
              title: 'dl_push_events',
              subtitle: 'GitHub dataset product',
              description: 'Release monitoring',
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
      },
    })

    render(<DomainDetailPage />)

    expect(screen.getByText('GitHub hub')).toBeInTheDocument()
    expect(screen.getAllByText('dl_push_events').length).toBeGreaterThan(0)
  })
})
