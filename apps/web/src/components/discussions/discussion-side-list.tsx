import { useDiscussions } from '@/hooks/use-discussions'
import { Link } from '@tanstack/react-router'
import { ArrowUp, MessageSquare } from 'lucide-react'

export function DiscussionSideList({ excludeId }: { excludeId?: string }) {
  const { data, isPending, isError } = useDiscussions({ sort: 'popular', pageSize: 10 })
  const items = (data?.data ?? []).filter((post) => post.id !== excludeId)

  if (isPending) {
    return <div className="h-32 animate-pulse rounded bg-[var(--muted)]" />
  }
  if (isError) {
    return <p className="text-sm text-red-600">목록을 불러오지 못했습니다.</p>
  }
  if (items.length === 0) {
    return <p className="text-sm text-[var(--muted-foreground)]">다른 토론이 없습니다.</p>
  }

  return (
    <ul className="space-y-2">
      {items.map((post) => (
        <li key={post.id}>
          <Link
            to="/discussions/$discussionId"
            params={{ discussionId: post.id }}
            className="block rounded-md border border-[var(--border)] bg-[var(--card)] p-3 hover:border-[var(--primary)]"
          >
            <p className="text-sm font-medium leading-snug">{post.title}</p>
            <div className="mt-1 flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
              <span className="inline-flex items-center gap-1">
                <ArrowUp className="h-3 w-3" />
                {post.upvote_count}
              </span>
              <span className="inline-flex items-center gap-1">
                <MessageSquare className="h-3 w-3" />
                {post.comment_count}
              </span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}
