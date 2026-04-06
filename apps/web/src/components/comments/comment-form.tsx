import { Button } from '@/components/ui/button'
import { useCreateComment } from '@/hooks/use-comments'
import { useAuth } from '@/lib/auth-context'
import type { CommentCategory } from '@pseudolab/shared-types'
import { MessageSquarePlus } from 'lucide-react'
import { type FormEvent, useState } from 'react'

type CommentFormProps = {
  datasetId: string
}

const CATEGORIES: { label: string; value: CommentCategory }[] = [
  { label: 'Limitation', value: 'limitation' },
  { label: 'Purpose', value: 'purpose' },
  { label: 'Usage', value: 'usage' },
]

export function CommentForm({ datasetId }: CommentFormProps) {
  const { isAuthenticated } = useAuth()
  const [category, setCategory] = useState<CommentCategory>('usage')
  const [content, setContent] = useState('')
  const mutation = useCreateComment()

  if (!isAuthenticated) {
    return (
      <p className="text-sm text-[var(--muted-foreground)]">
        댓글을 작성하려면 로그인이 필요합니다.
      </p>
    )
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = content.trim()
    if (!trimmed) return
    mutation.mutate(
      { datasetId, input: { category, content: trimmed } },
      {
        onSuccess: () => {
          setContent('')
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex items-center gap-2">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as CommentCategory)}
          className="rounded-md border border-[var(--border)] bg-[var(--background)] px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="이 데이터셋에 대한 의견을 남겨주세요..."
        className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] p-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
        rows={3}
        maxLength={5000}
      />
      <Button type="submit" size="sm" disabled={mutation.isPending || !content.trim()}>
        <MessageSquarePlus className="mr-1 h-4 w-4" />
        {mutation.isPending ? '작성 중...' : '댓글 작성'}
      </Button>
    </form>
  )
}
