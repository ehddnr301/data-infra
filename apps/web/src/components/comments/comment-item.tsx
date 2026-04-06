import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useDeleteComment, useUpdateComment } from '@/hooks/use-comments'
import { useAuth } from '@/lib/auth-context'
import type { DatasetComment } from '@pseudolab/shared-types'
import { Bot, Pencil, Trash2, User, X } from 'lucide-react'
import { useState } from 'react'

type CommentItemProps = {
  comment: DatasetComment
  datasetId: string
}

const CATEGORY_LABELS: Record<string, string> = {
  limitation: 'Limitation',
  purpose: 'Purpose',
  usage: 'Usage',
}

export function CommentItem({ comment, datasetId }: CommentItemProps) {
  const { auth } = useAuth()
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState(comment.content)
  const updateMutation = useUpdateComment()
  const deleteMutation = useDeleteComment()

  const isOwner = auth?.email === comment.user_email
  const isAiGenerated = comment.source !== 'human'
  const canEdit = isOwner || isAiGenerated
  const canDelete = isOwner

  function handleUpdate() {
    const trimmed = editContent.trim()
    if (!trimmed || trimmed === comment.content) {
      setEditing(false)
      return
    }
    updateMutation.mutate(
      { datasetId, commentId: comment.id, input: { content: trimmed } },
      { onSuccess: () => setEditing(false) },
    )
  }

  function handleDelete() {
    deleteMutation.mutate({ datasetId, commentId: comment.id })
  }

  return (
    <div className="space-y-2 rounded-md border border-[var(--border)] p-3">
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-[10px]">
          {CATEGORY_LABELS[comment.category] ?? comment.category}
        </Badge>
        {isAiGenerated && (
          <Badge variant="secondary" className="flex items-center gap-0.5 text-[10px]">
            <Bot className="h-2.5 w-2.5" />
            AI
          </Badge>
        )}
        <span className="flex items-center gap-1 text-xs text-[var(--muted-foreground)]">
          {isAiGenerated ? <Bot className="h-3 w-3" /> : <User className="h-3 w-3" />}
          {comment.user_name || comment.user_email}
        </span>
        <span className="text-[10px] text-[var(--muted-foreground)]">
          {formatRelativeTime(comment.created_at)}
        </span>
        <div className="ml-auto flex gap-1">
          {canEdit && !editing && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setEditContent(comment.content)
                setEditing(true)
              }}
              className="h-6 w-6 p-0"
            >
              <Pencil className="h-3 w-3" />
            </Button>
          )}
          {canDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="h-6 w-6 p-0 text-red-500 hover:text-red-600"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      {editing ? (
        <div className="space-y-2">
          <textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] p-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
            rows={3}
          />
          <div className="flex gap-1">
            <Button size="sm" onClick={handleUpdate} disabled={updateMutation.isPending}>
              저장
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
              <X className="mr-1 h-3 w-3" />
              취소
            </Button>
          </div>
        </div>
      ) : (
        <p className="whitespace-pre-wrap text-sm">{comment.content}</p>
      )}
    </div>
  )
}

function formatRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '방금 전'
  if (minutes < 60) return `${minutes}분 전`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`
  const days = Math.floor(hours / 24)
  return `${days}일 전`
}
