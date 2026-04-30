import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { DiscussionPost } from '@pseudolab/shared-types'
import { ArrowUp, MessageSquare } from 'lucide-react'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR')
}

export function DiscussionReader({ post }: { post: DiscussionPost }) {
  return (
    <Card className="space-y-4">
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

      <h1 className="text-2xl font-semibold">{post.title}</h1>

      <div className="flex flex-wrap gap-1">
        {post.linked.dataset && (
          <Badge variant="outline">dataset: {post.linked.dataset.name}</Badge>
        )}
        {post.linked.listing && (
          <Badge variant="outline">listing: {post.linked.listing.title}</Badge>
        )}
        {post.linked.query_history && (
          <Badge variant="outline">query: {post.linked.query_history.id}</Badge>
        )}
      </div>

      <p className="whitespace-pre-wrap text-sm leading-6 text-[var(--foreground)]">
        {post.content}
      </p>

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
  )
}
