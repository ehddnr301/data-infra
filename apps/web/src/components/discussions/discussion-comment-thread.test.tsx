import {
  DiscussionCommentThread,
  buildCommentTree,
} from '@/components/discussions/discussion-comment-thread'
import type { DiscussionComment } from '@pseudolab/shared-types'
import { render, screen } from '@testing-library/react'

function comment(
  id: string,
  parent: string | null,
  content: string,
  createdAt = '2026-04-20T12:00:00.000Z',
): DiscussionComment {
  return {
    id,
    post_id: 'post-1',
    parent_comment_id: parent,
    user_email: 'agent@pseudolab.org',
    user_name: 'agent-bot',
    source: 'ai-assisted',
    content,
    upvote_count: 0,
    created_at: createdAt,
  }
}

describe('buildCommentTree', () => {
  it('builds a nested tree from a flat list', () => {
    const tree = buildCommentTree([
      comment('a', null, 'A'),
      comment('b', 'a', 'B'),
      comment('c', 'b', 'C'),
      comment('d', null, 'D'),
    ])
    expect(tree).toHaveLength(2)
    expect(tree[0]?.children[0]?.comment.id).toBe('b')
    expect(tree[0]?.children[0]?.children[0]?.comment.id).toBe('c')
  })
})

describe('DiscussionCommentThread', () => {
  it('renders nested comments with depth attribute', () => {
    const comments: DiscussionComment[] = [
      comment('a', null, 'root'),
      comment('b', 'a', 'reply'),
      comment('c', 'b', 'nested reply'),
    ]
    render(<DiscussionCommentThread comments={comments} />)
    const rendered = screen.getAllByTestId('discussion-comment')
    const depths = rendered.map((el) => el.getAttribute('data-depth'))
    expect(depths).toContain('0')
    expect(depths).toContain('1')
    expect(depths).toContain('2')
    expect(screen.getByText('root')).toBeInTheDocument()
    expect(screen.getByText('reply')).toBeInTheDocument()
    expect(screen.getByText('nested reply')).toBeInTheDocument()
  })

  it('caps indentation depth at 6', () => {
    // chain of 8 comments — depths 0..7
    const chain: DiscussionComment[] = []
    let prev: string | null = null
    for (let i = 0; i < 8; i++) {
      const id = `c${i}`
      chain.push(comment(id, prev, `level ${i}`))
      prev = id
    }
    const { container } = render(<DiscussionCommentThread comments={chain} />)
    const all = container.querySelectorAll('[data-testid="discussion-comment"]')
    const depth6Inner = all[6]?.querySelector('div[style]') as HTMLElement | null
    const depth7Inner = all[7]?.querySelector('div[style]') as HTMLElement | null
    expect(depth6Inner?.style.marginLeft).toBe('144px')
    expect(depth7Inner?.style.marginLeft).toBe('144px')
  })

  it('renders empty placeholder when there are no comments', () => {
    render(<DiscussionCommentThread comments={[]} />)
    expect(screen.getByText('아직 댓글이 없습니다.')).toBeInTheDocument()
  })
})
