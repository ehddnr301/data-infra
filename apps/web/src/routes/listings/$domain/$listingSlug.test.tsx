import { ApiError } from '@/lib/api-client'
import { ListingDetailPage } from '@/routes/listings/$domain/$listingSlug'
import { fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { Mock } from 'vitest'

const CATALOG_API_BASE = ['/api/catalog', 'datasets'].join('/')

const navigateMock = vi.fn()

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <a href="/">{children}</a>,
  useNavigate: () => navigateMock,
  useParams: () => ({ domain: 'discord', listingSlug: 'messages.v1' }),
}))

vi.mock('@/components/lineage/lineage-viewer', () => ({
  LineageViewer: ({ onNavigateDataset }: { onNavigateDataset: (datasetId: string) => void }) => (
    <div>
      <div>lineage-viewer</div>
      <button type="button" onClick={() => onNavigateDataset('discord.watermarks.v1')}>
        navigate-lineage
      </button>
    </div>
  ),
}))

vi.mock('@/hooks/use-marketplace', () => ({
  useListing: vi.fn(),
}))

vi.mock('@/hooks/use-catalog', () => ({
  useColumns: vi.fn(),
  useDatasetPreview: vi.fn(),
}))

vi.mock('@/hooks/use-lineage', () => ({
  useLineage: vi.fn(),
}))

import { useColumns, useDatasetPreview } from '@/hooks/use-catalog'
import { useLineage } from '@/hooks/use-lineage'
import { useListing } from '@/hooks/use-marketplace'

const baseListingQuery = {
  isPending: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
  data: {
    data: {
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
        bio: 'Community analytics owners',
        avatar_url: null,
        contact_email: 'discord@pseudolab.org',
        slack_channel: '#discord-data',
      },
      business_need_tags: ['Moderation triage'],
      preview_available: true,
      has_pii: true,
      dataset: {
        id: 'discord.messages.v1',
        domain: 'discord',
        slug: 'messages.v1',
        name: 'Discord Messages',
        description: 'Community messages dataset',
        owner: 'qa',
        tags: ['discord', 'community'],
        purpose: 'Moderation triage and engagement review',
        limitations: ['Content can contain PII'],
        usage_examples: ['Review recent moderation spikes'],
        preview_available: true,
        has_pii: true,
        updated_at: '2025-01-10T00:00:00.000Z',
      },
      business_needs: [
        {
          id: 'need-1',
          title: 'Moderation triage',
          summary: 'Identify message anomalies quickly.',
          display_order: 1,
        },
      ],
      resources: [
        {
          id: 'resource-1',
          type: 'sql',
          title: 'Recent moderation query',
          summary: 'Inspect recent community activity.',
          url: null,
          content: 'SELECT * FROM discord_messages LIMIT 20;',
          display_order: 1,
          related_dataset_ids: ['discord.messages.v1'],
        },
      ],
      related_listings: [
        {
          id: 'listing-discord-watermarks',
          dataset_id: 'discord.watermarks.v1',
          domain: 'discord',
          slug: 'watermarks.v1',
          title: 'Discord Watermarks',
          subtitle: 'Discord dataset product',
          description: 'Collector recovery and freshness checks',
          category: 'operations',
          update_frequency: 'internal',
          coverage_summary: 'Collector progress dataset',
          documentation_url: `${CATALOG_API_BASE}/discord.watermarks.v1`,
          last_verified_at: '2025-01-09T00:00:00.000Z',
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
          business_need_tags: ['Collector recovery'],
          preview_available: false,
          has_pii: false,
        },
      ],
    },
  },
}

const githubListingQuery = {
  ...baseListingQuery,
  data: {
    data: {
      ...baseListingQuery.data.data,
      id: 'listing-github-push-events',
      dataset_id: 'github.push-events.v1',
      domain: 'github',
      slug: 'push-events.v1',
      title: 'GitHub Push Events',
      subtitle: 'Daily engineering activity feed',
      description: 'Repository activity with enrich-linked follow-up analysis.',
      category: 'engineering',
      coverage_summary: 'Push activity plus commit enrich detail',
      documentation_url: `${CATALOG_API_BASE}/github.push-events.v1`,
      owner: {
        ...baseListingQuery.data.data.owner,
        id: 'owner-github',
        slug: 'github-marketplace',
        display_name: 'GitHub Data Team',
        contact_email: 'github@pseudolab.org',
      },
      business_need_tags: ['Release cadence monitoring'],
      has_pii: false,
      dataset: {
        ...baseListingQuery.data.data.dataset,
        id: 'github.push-events.v1',
        domain: 'github',
        slug: 'push-events.v1',
        name: 'dl_push_events',
        description: 'Push activity dataset',
        purpose: 'Trace code contribution and extend into commit enrich evidence.',
        limitations: ['D1 rows are normalized indexes.'],
        usage_examples: [
          '최근 push가 많았던 repo를 찾은 뒤 enriched/commits 경로로 내려가 실제 변경 파일을 분석합니다.',
        ],
        has_pii: false,
      },
      resources: [
        {
          id: 'resource-github-push-sql',
          type: 'sql',
          title: 'Release cadence SQL',
          summary: 'Find candidate repos first.',
          url: null,
          content: 'SELECT repo_name FROM dl_push_events LIMIT 20;',
          display_order: 1,
          related_dataset_ids: ['github.push-events.v1'],
        },
        {
          id: 'resource-github-push-enrich-guide',
          type: 'documentation',
          title: 'Commit enrich lookup guide',
          summary: 'Follow commit candidates into enriched commit payloads.',
          url: null,
          content: 'github-archive-raw/enriched/commits/{owner}/{repo}/{commit_sha}.json',
          display_order: 2,
          related_dataset_ids: ['github.push-events.v1'],
        },
      ],
    },
  },
}

describe('ListingDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    navigateMock.mockReset()
    ;(useListing as Mock).mockReturnValue(baseListingQuery)
    ;(useColumns as Mock).mockImplementation((datasetId: string) => ({
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
      data: {
        data: [
          {
            dataset_id: datasetId,
            column_name: 'content',
            data_type: 'TEXT',
            description: `${datasetId} column`,
            is_pii: datasetId === 'discord.messages.v1',
            examples: null,
          },
        ],
      },
    }))
    ;(useDatasetPreview as Mock).mockImplementation((datasetId: string) => ({
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
      data: {
        data: {
          datasetId,
          source: { kind: 'mapped-table', table: 'discord_messages' },
          columns: ['content'],
          rows: [{ content: `${datasetId} row` }],
          meta: { limit: 10, returned: 1, total_rows: 1 },
        },
      },
    }))
    ;(useLineage as Mock).mockImplementation((datasetId: string) => ({
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
      data: {
        data: {
          version: 1,
          nodes: [
            { id: datasetId, type: 'dataset', position: { x: 0, y: 0 }, data: { datasetId } },
          ],
          edges: [],
        },
      },
    }))
  })

  it('renders purpose, dataset explorer, resources, and related listings', () => {
    render(<ListingDetailPage />)

    expect(screen.getByText('Discord Messages')).toBeInTheDocument()
    expect(screen.getAllByText('Moderation triage and engagement review').length).toBeGreaterThan(0)
    expect(screen.getByText('Content can contain PII')).toBeInTheDocument()
    expect(screen.getByText('Review recent moderation spikes')).toBeInTheDocument()
    expect(screen.getByText('Recent moderation query')).toBeInTheDocument()
    expect(screen.getByText('Discord Watermarks')).toBeInTheDocument()
    expect(screen.getByText('lineage-viewer')).toBeInTheDocument()
  })

  it('removes owner and dataset identity side panels to keep the content area wider', () => {
    render(<ListingDetailPage />)

    expect(screen.queryByRole('heading', { name: 'Owner' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Dataset identity' })).not.toBeInTheDocument()
  })

  it('renders GitHub enrich quick-start guidance when the listing is github', () => {
    ;(useListing as Mock).mockReturnValue(githubListingQuery)

    render(<ListingDetailPage />)

    expect(screen.getByText('Resources & analysis quick start')).toBeInTheDocument()
    expect(
      screen.getByText(
        'SQL로 활동 후보를 찾고 documentation/notebook 리소스로 enrich evidence까지 내려가 보세요.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('Commit enrich lookup guide')).toBeInTheDocument()
    expect(
      screen.getByText('github-archive-raw/enriched/commits/{owner}/{repo}/{commit_sha}.json'),
    ).toBeInTheDocument()
  })

  it('keeps preview tables horizontally scrollable and truncates long values', () => {
    const longPreviewValue = 'discord moderation triage preview content '.repeat(12).trim()
    ;(useDatasetPreview as Mock).mockReturnValue({
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
      data: {
        data: {
          datasetId: 'discord.messages.v1',
          source: { kind: 'mapped-table', table: 'discord_messages' },
          columns: ['message_text'],
          rows: [{ message_text: longPreviewValue }],
          meta: { limit: 10, returned: 1, total_rows: 1 },
        },
      },
    })

    render(<ListingDetailPage />)

    const previewTable = screen.getByRole('table')
    expect(previewTable.parentElement).toHaveClass('overflow-x-auto')

    const previewHeader = screen.getByTitle('message_text')
    expect(previewHeader).toHaveClass('truncate', 'whitespace-nowrap')

    const previewCell = screen.getByTitle(longPreviewValue)
    expect(previewCell).toHaveClass('truncate', 'whitespace-nowrap')
  })

  it('navigates to canonical listing detail from lineage interactions', () => {
    render(<ListingDetailPage />)

    fireEvent.click(screen.getByRole('button', { name: 'navigate-lineage' }))

    expect(navigateMock).toHaveBeenCalledWith({
      to: '/listings/$domain/$listingSlug',
      params: { domain: 'discord', listingSlug: 'watermarks.v1' },
    })
  })

  it('renders not found state for 404 errors', () => {
    ;(useListing as Mock).mockReturnValue({
      isPending: false,
      isError: true,
      error: new ApiError(404, null),
      refetch: vi.fn(),
      data: undefined,
    })

    render(<ListingDetailPage />)

    expect(screen.getByText('리스팅을 찾을 수 없습니다.')).toBeInTheDocument()
  })
})
