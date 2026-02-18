import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useColumns, useDataset } from '@/hooks/use-catalog'
import { Link, useParams } from '@tanstack/react-router'
import { DatasetDetailSkeleton } from '@/components/skeleton/dataset-skeleton'
import { ErrorCard } from '@/components/error-card'
import type { CatalogColumn } from '@pseudolab/shared-types'

function parseTags(tags: string | null): string[] {
  if (!tags) return []
  try {
    const parsed = JSON.parse(tags)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return tags.includes(',') ? tags.split(',').map((t) => t.trim()).filter(Boolean) : [tags.trim()]
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR')
}

function parseExamples(examples: string | null): string[] {
  if (!examples) return []
  try {
    const parsed = JSON.parse(examples)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-xs text-[var(--muted-foreground)]">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  )
}

function ColumnTable({
  columns,
  onSelect,
}: {
  columns: CatalogColumn[]
  onSelect: (col: CatalogColumn) => void
}) {
  return (
    <Table>
      <THead>
        <TR>
          <TH>컬럼명</TH>
          <TH>데이터 타입</TH>
          <TH>설명</TH>
          <TH>PII</TH>
        </TR>
      </THead>
      <TBody>
        {columns.map((col) => (
          <TR
            key={col.column_name}
            className="hover:bg-[var(--muted)]/50 cursor-pointer"
            onClick={() => onSelect(col)}
          >
            <TD>
              <span className="font-mono text-sm">{col.column_name}</span>
            </TD>
            <TD>
              <Badge variant="outline">{col.data_type}</Badge>
            </TD>
            <TD>
              <span className="text-sm text-[var(--muted-foreground)]">
                {col.description ?? '-'}
              </span>
            </TD>
            <TD>
              {col.is_pii ? (
                <Badge variant="secondary">PII</Badge>
              ) : (
                <span className="text-xs text-[var(--muted-foreground)]">-</span>
              )}
            </TD>
          </TR>
        ))}
      </TBody>
    </Table>
  )
}

function ColumnCard({
  column,
  onSelect,
}: {
  column: CatalogColumn
  onSelect: (col: CatalogColumn) => void
}) {
  return (
    <Card
      className="p-3 cursor-pointer hover:bg-[var(--muted)]/50"
      onClick={() => onSelect(column)}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-sm font-medium">{column.column_name}</span>
        <div className="flex items-center gap-1">
          <Badge variant="outline">{column.data_type}</Badge>
          {column.is_pii && <Badge variant="secondary">PII</Badge>}
        </div>
      </div>
      {column.description && (
        <p className="text-xs text-[var(--muted-foreground)] mt-1">{column.description}</p>
      )}
    </Card>
  )
}

function ColumnDetailPanel({
  column,
  onClose,
}: {
  column: CatalogColumn | null
  onClose: () => void
}) {
  const examples = parseExamples(column?.examples ?? null)

  return (
    <Sheet open={!!column} onOpenChange={(v) => { if (!v) onClose() }}>
      <SheetContent>
        <SheetHeader onClose={onClose}>
          <SheetTitle>{column?.column_name}</SheetTitle>
        </SheetHeader>
        {column && (
          <div className="space-y-4">
            <div className="space-y-1">
              <p className="text-xs text-[var(--muted-foreground)]">데이터 타입</p>
              <Badge variant="outline">{column.data_type}</Badge>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-[var(--muted-foreground)]">설명</p>
              <p className="text-sm">{column.description ?? '설명 없음'}</p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-[var(--muted-foreground)]">PII 여부</p>
              {column.is_pii ? (
                <Badge variant="secondary">PII 포함</Badge>
              ) : (
                <p className="text-sm">해당 없음</p>
              )}
            </div>
            {examples.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-[var(--muted-foreground)]">예시 값</p>
                <div className="flex flex-wrap gap-1">
                  {examples.map((ex, i) => (
                    <code
                      key={i}
                      className="text-xs bg-[var(--muted)] px-1.5 py-0.5 rounded font-mono"
                    >
                      {ex}
                    </code>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

export function DatasetDetailPage() {
  const { datasetId } = useParams({ from: '/datasets/$datasetId' })
  const datasetQuery = useDataset(datasetId)
  const columnsQuery = useColumns(datasetId)
  const [selectedColumn, setSelectedColumn] = useState<CatalogColumn | null>(null)

  if (datasetQuery.isPending) {
    return (
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Link to="/datasets">
            <Button variant="ghost" size="sm">← 목록</Button>
          </Link>
        </div>
        <DatasetDetailSkeleton />
      </section>
    )
  }

  if (datasetQuery.isError) {
    return (
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Link to="/datasets">
            <Button variant="ghost" size="sm">← 목록</Button>
          </Link>
        </div>
        <ErrorCard
          message="데이터셋 정보를 불러올 수 없습니다."
          onRetry={() => datasetQuery.refetch()}
        />
      </section>
    )
  }

  const dataset = datasetQuery.data?.data
  if (!dataset) return null

  const columns = columnsQuery.data?.data ?? []
  const tags = parseTags(dataset.tags)

  return (
    <section className="space-y-6">
      {/* Back navigation */}
      <div className="flex items-center gap-2">
        <Link to="/datasets">
          <Button variant="ghost" size="sm">← 목록</Button>
        </Link>
      </div>

      {/* Title + domain badge */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-2xl font-semibold">{dataset.name}</h1>
          <Badge>{dataset.domain}</Badge>
        </div>
        {dataset.description && (
          <p className="text-sm text-[var(--muted-foreground)]">{dataset.description}</p>
        )}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <Badge key={tag} variant="secondary">{tag}</Badge>
            ))}
          </div>
        )}
      </div>

      {/* Metadata grid */}
      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <MetaItem label="소유자" value={dataset.owner ?? '미지정'} />
          <MetaItem label="컬럼 수" value={columnsQuery.isPending ? '...' : String(columns.length)} />
          <MetaItem label="생성일" value={formatDate(dataset.created_at)} />
          <MetaItem label="수정일" value={formatDate(dataset.updated_at)} />
        </div>
      </Card>

      <Separator />

      {/* Column list */}
      <div className="space-y-2">
        <h2 className="text-lg font-semibold">컬럼 목록</h2>

        {columnsQuery.isPending ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-10 bg-[var(--muted)] animate-pulse rounded" />
            ))}
          </div>
        ) : columnsQuery.isError ? (
          <ErrorCard
            message="컬럼 정보를 불러올 수 없습니다."
            onRetry={() => columnsQuery.refetch()}
          />
        ) : columns.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">컬럼 정보가 없습니다.</p>
        ) : (
          <>
            {/* Desktop: table */}
            <div className="hidden sm:block">
              <ColumnTable columns={columns} onSelect={setSelectedColumn} />
            </div>

            {/* Mobile: cards */}
            <div className="block sm:hidden space-y-2">
              {columns.map((col) => (
                <ColumnCard key={col.column_name} column={col} onSelect={setSelectedColumn} />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Column detail side panel */}
      <ColumnDetailPanel
        column={selectedColumn}
        onClose={() => setSelectedColumn(null)}
      />
    </section>
  )
}
