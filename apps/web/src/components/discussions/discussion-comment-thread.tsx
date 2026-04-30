import { Badge } from '@/components/ui/badge'
import type { DiscussionComment } from '@pseudolab/shared-types'
import { ArrowUp } from 'lucide-react'

const MAX_INDENT_DEPTH = 6
const INDENT_PX = 24

type CommentNode = {
  comment: DiscussionComment
  children: CommentNode[]
}

export function buildCommentTree(comments: DiscussionComment[]): CommentNode[] {
  const byId = new Map<string, CommentNode>()
  for (const c of comments) {
    byId.set(c.id, { comment: c, children: [] })
  }
  const roots: CommentNode[] = []
  for (const c of comments) {
    const node = byId.get(c.id)
    if (!node) continue
    if (c.parent_comment_id) {
      const parent = byId.get(c.parent_comment_id)
      if (parent) {
        parent.children.push(node)
        continue
      }
    }
    roots.push(node)
  }
  return roots
}

function CommentRow({ node, depth }: { node: CommentNode; depth: number }) {
  const indentPx = Math.min(depth, MAX_INDENT_DEPTH) * INDENT_PX
  const { comment } = node
  return (
    <div data-testid="discussion-comment" data-depth={depth}>
      <div
        className="rounded-md border border-[var(--border)] bg-[var(--card)] p-3"
        style={{ marginLeft: `${indentPx}px` }}
      >
        <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted-foreground)]">
          <Badge variant="outline" className="text-xs">
            {comment.source}
          </Badge>
          <span>{comment.user_name || comment.user_email}</span>
          <span>·</span>
          <span>{new Date(comment.created_at).toLocaleString('ko-KR')}</span>
        </div>
        <p className="mt-2 whitespace-pre-wrap text-sm">{comment.content}</p>
        <div className="mt-2 flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
          <ArrowUp className="h-3 w-3" />
          {comment.upvote_count}
        </div>
      </div>
      {node.children.length > 0 && (
        <div className="mt-2 space-y-2">
          {node.children.map((child) => (
            <CommentRow key={child.comment.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export function DiscussionCommentThread({ comments }: { comments: DiscussionComment[] }) {
  const tree = buildCommentTree(comments)
  if (tree.length === 0) {
    return <p className="text-sm text-[var(--muted-foreground)]">아직 댓글이 없습니다.</p>
  }
  return (
    <div className="space-y-2">
      {tree.map((node) => (
        <CommentRow key={node.comment.id} node={node} depth={0} />
      ))}
    </div>
  )
}
