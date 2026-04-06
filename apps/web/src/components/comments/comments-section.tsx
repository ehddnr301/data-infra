import { CommentForm } from '@/components/comments/comment-form'
import { CommentList } from '@/components/comments/comment-list'
import { Card } from '@/components/ui/card'
import { MessageSquare } from 'lucide-react'

type CommentsSectionProps = {
  datasetId: string
}

export function CommentsSection({ datasetId }: CommentsSectionProps) {
  return (
    <Card className="space-y-4 p-4">
      <div className="flex items-center gap-2">
        <MessageSquare className="h-4 w-4" />
        <h2 className="text-sm font-semibold">댓글</h2>
      </div>
      <CommentForm datasetId={datasetId} />
      <div className="border-t border-[var(--border)] pt-4">
        <CommentList datasetId={datasetId} />
      </div>
    </Card>
  )
}
