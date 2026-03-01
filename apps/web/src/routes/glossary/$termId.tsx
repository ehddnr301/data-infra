import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useGlossaryTerm, useGlossaryTerms } from '@/hooks/use-glossary'
import { Link, useParams } from '@tanstack/react-router'

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR')
}

export function GlossaryDetailPage() {
  const { termId } = useParams({ from: '/glossary/$termId' })
  const termQuery = useGlossaryTerm(termId)
  const relationLookupQuery = useGlossaryTerms({ page: 1, pageSize: 200 })

  if (termQuery.isPending) {
    return (
      <section className="space-y-4">
        <div className="h-8 rounded bg-[var(--muted)] animate-pulse" />
        <div className="h-40 rounded bg-[var(--muted)] animate-pulse" />
      </section>
    )
  }

  if (termQuery.isError) {
    return (
      <ErrorCard message="용어 상세를 불러올 수 없습니다." onRetry={() => termQuery.refetch()} />
    )
  }

  const term = termQuery.data?.data
  if (!term) {
    return <EmptyState title="용어를 찾을 수 없습니다." />
  }

  const termById = new Map((relationLookupQuery.data?.data ?? []).map((item) => [item.id, item]))

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Link to="/glossary">
            <Button variant="ghost" size="sm">
              ← 목록
            </Button>
          </Link>
          <Badge>{term.domain}</Badge>
        </div>
        <Link to="/glossary/$termId/edit" params={{ termId: term.id }}>
          <Button size="sm" variant="outline">
            수정
          </Button>
        </Link>
      </div>

      <Card className="p-4 space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">{term.term}</h1>
          <p className="text-sm text-[var(--muted-foreground)]">{term.definition}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-[var(--muted-foreground)]">생성일</p>
            <p>{formatDate(term.created_at)}</p>
          </div>
          <div>
            <p className="text-[var(--muted-foreground)]">수정일</p>
            <p>{formatDate(term.updated_at)}</p>
          </div>
        </div>
      </Card>

      <Card className="p-4 space-y-3">
        <h2 className="font-semibold">관련 용어</h2>
        {term.related_terms.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">연결된 용어가 없습니다.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {term.related_terms.map((relatedId) => {
              const related = termById.get(relatedId)

              if (!related) {
                return (
                  <span
                    key={relatedId}
                    className="rounded border border-dashed border-[var(--border)] px-2 py-1 text-xs text-[var(--muted-foreground)]"
                  >
                    {relatedId} (삭제되었거나 존재하지 않음)
                  </span>
                )
              }

              return (
                <Link key={relatedId} to="/glossary/$termId" params={{ termId: relatedId }}>
                  <Badge variant="secondary">{related.term}</Badge>
                </Link>
              )
            })}
          </div>
        )}
      </Card>
    </section>
  )
}
