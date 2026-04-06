import { CommentItem } from '@/components/comments/comment-item'
import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { Button } from '@/components/ui/button'
import { useComments } from '@/hooks/use-comments'
import type { CommentCategory, CommentSource } from '@pseudolab/shared-types'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'

type CommentListProps = {
  datasetId: string
}

const CATEGORY_FILTERS: { label: string; value: CommentCategory | undefined }[] = [
  { label: '전체', value: undefined },
  { label: 'Limitation', value: 'limitation' },
  { label: 'Purpose', value: 'purpose' },
  { label: 'Usage', value: 'usage' },
]

const SOURCE_FILTERS: { label: string; value: CommentSource | undefined }[] = [
  { label: '전체', value: undefined },
  { label: 'Human', value: 'human' },
  { label: 'AI', value: 'ai-auto' },
]

export function CommentList({ datasetId }: CommentListProps) {
  const [category, setCategory] = useState<CommentCategory | undefined>()
  const [source, setSource] = useState<CommentSource | undefined>()
  const [page, setPage] = useState(1)

  const { data, isPending, isError, refetch } = useComments(datasetId, {
    category,
    source,
    page,
    pageSize: 20,
  })

  const comments = data?.data ?? []
  const pagination = data?.pagination

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex gap-1">
          {CATEGORY_FILTERS.map((f) => (
            <Button
              key={f.label}
              variant={category === f.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setCategory(f.value)
                setPage(1)
              }}
            >
              {f.label}
            </Button>
          ))}
        </div>
        <div className="h-4 w-px bg-[var(--border)]" />
        <div className="flex gap-1">
          {SOURCE_FILTERS.map((f) => (
            <Button
              key={f.label}
              variant={source === f.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setSource(f.value)
                setPage(1)
              }}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isPending ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded bg-[var(--muted)]" />
          ))}
        </div>
      ) : isError ? (
        <ErrorCard onRetry={() => void refetch()} />
      ) : comments.length === 0 ? (
        <EmptyState title="댓글 없음" description="아직 작성된 댓글이 없습니다." />
      ) : (
        <div className="space-y-2">
          {comments.map((comment) => (
            <CommentItem key={comment.id} comment={comment} datasetId={datasetId} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {pagination && pagination.totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-xs text-[var(--muted-foreground)]">
            {page} / {pagination.totalPages}
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={page >= pagination.totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}
