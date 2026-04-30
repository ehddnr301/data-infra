import { DiscussionCommentThread } from '@/components/discussions/discussion-comment-thread'
import { DiscussionReader } from '@/components/discussions/discussion-reader'
import { DiscussionSideList } from '@/components/discussions/discussion-side-list'
import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useDiscussion, useDiscussionComments } from '@/hooks/use-discussions'
import { ApiError } from '@/lib/api-client'
import { Link, useParams } from '@tanstack/react-router'

export function DiscussionDetailPage() {
  const { discussionId } = useParams({ from: '/discussions/$discussionId' })
  const postQuery = useDiscussion(discussionId)
  const commentsQuery = useDiscussionComments(discussionId)

  if (postQuery.isPending) {
    return <div className="h-32 animate-pulse rounded bg-[var(--muted)]" />
  }
  if (postQuery.isError) {
    const error = postQuery.error as Error
    if (error instanceof ApiError && error.status === 404) {
      return (
        <Card className="space-y-3">
          <h1 className="text-xl font-semibold">토론을 찾을 수 없습니다.</h1>
          <Link to="/discussions">
            <Button type="button" variant="outline">
              목록으로 이동
            </Button>
          </Link>
        </Card>
      )
    }
    return <ErrorCard message={error.message} onRetry={postQuery.refetch} />
  }

  const post = postQuery.data?.data
  if (!post) {
    return <EmptyState title="토론 데이터가 없습니다." />
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center gap-2">
        <Link to="/discussions">
          <Button type="button" variant="outline" size="sm">
            ← 목록
          </Button>
        </Link>
      </div>

      <div className="grid gap-6 md:grid-cols-[1fr_18rem]">
        <div className="space-y-6">
          <DiscussionReader post={post} />

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">댓글</h2>
            {commentsQuery.isPending && (
              <div className="h-16 animate-pulse rounded bg-[var(--muted)]" />
            )}
            {commentsQuery.isError && (
              <ErrorCard
                message={(commentsQuery.error as Error).message}
                onRetry={commentsQuery.refetch}
              />
            )}
            {commentsQuery.data && <DiscussionCommentThread comments={commentsQuery.data.data} />}
          </Card>
        </div>

        <aside className="hidden md:block">
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
              인기 토론
            </h2>
            <DiscussionSideList excludeId={post.id} />
          </div>
        </aside>
      </div>
    </section>
  )
}
