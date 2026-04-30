import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { DiscussionPostSummary } from '@pseudolab/shared-types'
import { Link } from '@tanstack/react-router'
import { ArrowUp, MessageSquare } from 'lucide-react'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR')
}

function LinkedBadges({ post }: { post: DiscussionPostSummary }) {
  const items: { key: string; label: string }[] = []
  if (post.linked.dataset) items.push({ key: 'd', label: `dataset: ${post.linked.dataset.name}` })
  if (post.linked.listing) items.push({ key: 'l', label: `listing: ${post.linked.listing.title}` })
  if (post.linked.query_history)
    items.push({ key: 'q', label: `query: ${post.linked.query_history.id}` })
  if (items.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((item) => (
        <Badge key={item.key} variant="outline" className="text-xs">
          {item.label}
        </Badge>
      ))}
    </div>
  )
}

export function DiscussionList({ items }: { items: DiscussionPostSummary[] }) {
  return (
    <div className="grid gap-3">
      {items.map((post) => (
        <Link
          key={post.id}
          to="/discussions/$discussionId"
          params={{ discussionId: post.id }}
          className="block"
        >
          <article data-testid="discussion-card">
            <Card className="space-y-3 transition-colors hover:border-[var(--primary)]">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{post.source}</Badge>
                <span className="text-xs text-[var(--muted-foreground)]">
                  {post.user_name || post.user_email}
                </span>
                <span className="text-xs text-[var(--muted-foreground)]">·</span>
                <span className="text-xs text-[var(--muted-foreground)]">
                  {formatDate(post.created_at)}
                </span>
              </div>

              <div className="space-y-1">
                <h2 className="text-lg font-semibold">{post.title}</h2>
                <p className="text-sm text-[var(--muted-foreground)]">{post.excerpt}</p>
              </div>

              <LinkedBadges post={post} />

              <div className="flex items-center gap-3 text-xs text-[var(--muted-foreground)]">
                <span className="inline-flex items-center gap-1">
                  <ArrowUp className="h-3 w-3" />
                  {post.upvote_count}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MessageSquare className="h-3 w-3" />
                  {post.comment_count}
                </span>
              </div>
            </Card>
          </article>
        </Link>
      ))}
    </div>
  )
}
