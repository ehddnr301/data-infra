import { useState } from 'react'
import { LayoutGrid, List } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table'
import { useDatasets } from '@/hooks/use-catalog'
import { Link } from '@tanstack/react-router'
import { DatasetListSkeleton } from '@/components/skeleton/dataset-skeleton'
import { ErrorCard } from '@/components/error-card'
import { EmptyState } from '@/components/empty-state'
import type { CatalogDataset, DomainName } from '@pseudolab/shared-types'

function parseTags(tags: string | null): string[] {
  if (!tags) return []
  try {
    const parsed = JSON.parse(tags)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return tags.includes(',') ? tags.split(',').map((t) => t.trim()).filter(Boolean) : [tags.trim()]
  }
}

function DatasetCard({ dataset }: { dataset: CatalogDataset }) {
  const tags = parseTags(dataset.tags)
  return (
    <Link to="/datasets/$datasetId" params={{ datasetId: dataset.id }} className="block">
      <Card className="h-full hover:border-[var(--primary)] transition-colors cursor-pointer p-4 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <p className="font-medium text-sm leading-tight">{dataset.name}</p>
          <Badge className="shrink-0">{dataset.domain}</Badge>
        </div>
        {dataset.description && (
          <p className="text-sm text-[var(--muted-foreground)] line-clamp-2">{dataset.description}</p>
        )}
        {dataset.owner && (
          <p className="text-xs text-[var(--muted-foreground)]">소유자: {dataset.owner}</p>
        )}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <Badge key={tag} className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </Card>
    </Link>
  )
}

const DOMAINS: Array<{ label: string; value: DomainName | undefined }> = [
  { label: '전체', value: undefined },
  { label: 'github', value: 'github' },
  { label: 'discord', value: 'discord' },
  { label: 'linkedin', value: 'linkedin' },
  { label: 'members', value: 'members' },
]

export function DatasetsPage() {
  const [search, setSearch] = useState('')
  const [domainFilter, setDomainFilter] = useState<DomainName | undefined>(undefined)
  const [view, setView] = useState<'table' | 'card'>('table')

  const { data, isPending, isError, error, refetch } = useDatasets({
    domain: domainFilter,
    page: 1,
    pageSize: 20,
  })

  const filtered = data?.data.filter((d) => {
    if (!search) return true
    const q = search.toLowerCase()
    return d.name.toLowerCase().includes(q) || (d.description ?? '').toLowerCase().includes(q)
  }) ?? []

  return (
    <section className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">데이터셋</h1>
        <div className="flex items-center gap-2">
          <Input
            className="w-full sm:w-60"
            placeholder="이름 또는 설명 검색"
            value={search}
            onChange={(e) => setSearch((e.target as HTMLInputElement).value)}
          />
          <Button
            variant={view === 'table' ? 'default' : 'outline'}
            size="sm"
            className="px-2"
            onClick={() => setView('table')}
            aria-label="테이블 보기"
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant={view === 'card' ? 'default' : 'outline'}
            size="sm"
            className="px-2"
            onClick={() => setView('card')}
            aria-label="카드 보기"
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {DOMAINS.map(({ label, value }) => (
          <Button
            key={label}
            variant={domainFilter === value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setDomainFilter(value)}
          >
            {label}
          </Button>
        ))}
      </div>

      {isPending && <DatasetListSkeleton />}

      {isError && (
        <ErrorCard
          message={(error as Error).message || '데이터셋 조회 중 오류가 발생했습니다.'}
          onRetry={refetch}
        />
      )}

      {!isPending && !isError && filtered.length === 0 && (
        <EmptyState title="데이터셋이 없습니다." />
      )}

      {!isPending && !isError && filtered.length > 0 && view === 'card' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((dataset) => (
            <DatasetCard key={dataset.id} dataset={dataset} />
          ))}
        </div>
      )}

      {!isPending && !isError && filtered.length > 0 && view === 'table' && (
        <Card>
          <Table>
            <THead>
              <TR>
                <TH>이름</TH>
                <TH>도메인</TH>
                <TH>설명</TH>
              </TR>
            </THead>
            <TBody>
              {filtered.map((dataset) => (
                <TR key={dataset.id}>
                  <TD>
                    <Link to="/datasets/$datasetId" params={{ datasetId: dataset.id }}>
                      {dataset.name}
                    </Link>
                  </TD>
                  <TD>
                    <Badge>{dataset.domain}</Badge>
                  </TD>
                  <TD>{dataset.description}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </Card>
      )}
    </section>
  )
}
