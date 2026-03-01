import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table'
import { useGlossaryTerms } from '@/hooks/use-glossary'
import type { DomainName } from '@pseudolab/shared-types'
import { Link } from '@tanstack/react-router'
import { useMemo, useState } from 'react'

const DOMAINS: Array<{ label: string; value: DomainName | undefined }> = [
  { label: '전체', value: undefined },
  { label: 'github', value: 'github' },
  { label: 'discord', value: 'discord' },
  { label: 'linkedin', value: 'linkedin' },
  { label: 'members', value: 'members' },
]

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR')
}

export function GlossaryListPage() {
  const [query, setQuery] = useState('')
  const [domain, setDomain] = useState<DomainName | undefined>(undefined)

  const glossaryQuery = useGlossaryTerms({
    q: query || undefined,
    domain,
    page: 1,
    pageSize: 100,
  })

  const terms = glossaryQuery.data?.data ?? []
  const total = useMemo(() => glossaryQuery.data?.pagination.total ?? 0, [glossaryQuery.data])

  return (
    <section className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">용어집</h1>
          <p className="text-sm text-[var(--muted-foreground)]">총 {total}개 용어</p>
        </div>
        <Link to="/glossary/new">
          <Button size="sm">용어 추가</Button>
        </Link>
      </div>

      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          className="sm:w-80"
          placeholder="용어 또는 정의 검색"
          value={query}
          onChange={(event) => setQuery((event.target as HTMLInputElement).value)}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {DOMAINS.map(({ label, value }) => (
          <Button
            key={label}
            size="sm"
            variant={domain === value ? 'default' : 'outline'}
            onClick={() => setDomain(value)}
          >
            {label}
          </Button>
        ))}
      </div>

      {glossaryQuery.isPending ? (
        <Card className="p-4 space-y-2">
          {['s1', 's2', 's3', 's4', 's5'].map((key) => (
            <div key={key} className="h-8 rounded bg-[var(--muted)] animate-pulse" />
          ))}
        </Card>
      ) : null}

      {glossaryQuery.isError ? (
        <ErrorCard
          message={(glossaryQuery.error as Error).message || '용어집 조회 중 오류가 발생했습니다.'}
          onRetry={() => glossaryQuery.refetch()}
        />
      ) : null}

      {!glossaryQuery.isPending && !glossaryQuery.isError && terms.length === 0 ? (
        <EmptyState title="용어가 없습니다." description="새 용어를 추가해보세요." />
      ) : null}

      {!glossaryQuery.isPending && !glossaryQuery.isError && terms.length > 0 ? (
        <Card>
          <Table>
            <THead>
              <TR>
                <TH>용어</TH>
                <TH>도메인</TH>
                <TH>관련 용어 수</TH>
                <TH>수정일</TH>
              </TR>
            </THead>
            <TBody>
              {terms.map((term) => (
                <TR key={term.id}>
                  <TD>
                    <Link to="/glossary/$termId" params={{ termId: term.id }}>
                      {term.term}
                    </Link>
                  </TD>
                  <TD>{term.domain}</TD>
                  <TD>{term.related_terms.length}</TD>
                  <TD>{formatDate(term.updated_at)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </Card>
      ) : null}
    </section>
  )
}
