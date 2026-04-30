import { DiscussionsListPage } from '@/routes/discussions'
import type { DiscussionPostSummary } from '@pseudolab/shared-types'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { Mock } from 'vitest'

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <a href="/">{children}</a>,
}))

vi.mock('@/hooks/use-discussions', () => ({
  useDiscussions: vi.fn(),
}))

import { useDiscussions } from '@/hooks/use-discussions'

const baseQuery = {
  isPending: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
}

const samplePost: DiscussionPostSummary = {
  id: 'post-1',
  title: 'Sample discussion',
  excerpt: 'Short excerpt of the post',
  user_email: 'agent@pseudolab.org',
  user_name: 'agent-bot',
  source: 'ai-assisted',
  dataset_id: 'github.push-events.v1',
  listing_id: null,
  query_history_id: null,
  upvote_count: 3,
  comment_count: 1,
  created_at: '2026-04-20T12:00:00.000Z',
  linked: {
    dataset: { id: 'github.push-events.v1', name: 'Push Events' },
    listing: null,
    query_history: null,
  },
}

describe('DiscussionsListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders post cards when items exist', () => {
    ;(useDiscussions as Mock).mockReturnValue({
      ...baseQuery,
      data: { data: [samplePost] },
    })
    render(<DiscussionsListPage />)
    expect(screen.getByText('Sample discussion')).toBeInTheDocument()
    expect(screen.getByText('Short excerpt of the post')).toBeInTheDocument()
  })

  it('renders the empty state when no items', () => {
    ;(useDiscussions as Mock).mockReturnValue({
      ...baseQuery,
      data: { data: [] },
    })
    render(<DiscussionsListPage />)
    expect(screen.getByText('아직 토론이 없습니다.')).toBeInTheDocument()
  })
})
