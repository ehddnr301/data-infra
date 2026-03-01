import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { LineageViewer } from '@/components/lineage/lineage-viewer'
import { DatasetDetailSkeleton } from '@/components/skeleton/dataset-skeleton'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table'
import { useColumns, useDataset, useDatasetPreview } from '@/hooks/use-catalog'
import { useLineage, useSaveLineage } from '@/hooks/use-lineage'
import type { CatalogColumn, LineageGraph } from '@pseudolab/shared-types'
import { Link, useNavigate, useParams } from '@tanstack/react-router'
import { useMemo, useState } from 'react'

function parseTags(tags: string | null): string[] {
  if (!tags) return []
  try {
    const parsed = JSON.parse(tags)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return tags.includes(',')
      ? tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean)
      : [tags.trim()]
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

type DatasetDetailTab = 'columns' | 'preview' | 'lineage'
type PreviewSortDirection = 'asc' | 'desc'

const PREVIEW_LIMIT_OPTIONS = [10, 20, 50] as const

function parseJsonLike(value: unknown): unknown | null {
  if (typeof value !== 'string') {
    return null
  }

  try {
    const parsed = JSON.parse(value)
    if (typeof parsed === 'object' && parsed !== null) {
      return parsed
    }
    return null
  } catch {
    return null
  }
}

function getExpandedJsonValue(value: unknown): unknown | null {
  if (Array.isArray(value)) {
    return value
  }

  if (value && typeof value === 'object') {
    return value
  }

  return parseJsonLike(value)
}

function formatPreviewValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '-'
  }

  if (typeof value === 'string') {
    return value
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }

  if (Array.isArray(value) || typeof value === 'object') {
    return JSON.stringify(value)
  }

  return String(value)
}

function comparePreviewValues(a: unknown, b: unknown): number {
  if (a === b) {
    return 0
  }

  if (a === null || a === undefined) {
    return -1
  }

  if (b === null || b === undefined) {
    return 1
  }

  if (typeof a === 'number' && typeof b === 'number') {
    return a - b
  }

  if (typeof a === 'boolean' && typeof b === 'boolean') {
    if (a === b) {
      return 0
    }
    return a ? 1 : -1
  }

  return formatPreviewValue(a).localeCompare(formatPreviewValue(b), 'ko-KR', {
    numeric: true,
    sensitivity: 'base',
  })
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
    <Sheet
      open={!!column}
      onOpenChange={(v) => {
        if (!v) onClose()
      }}
    >
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
                  {examples.map((ex) => (
                    <code
                      key={`${column.column_name}:${ex}`}
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
  const navigate = useNavigate()
  const { datasetId } = useParams({ from: '/datasets/$datasetId' })
  const datasetQuery = useDataset(datasetId)
  const columnsQuery = useColumns(datasetId)
  const [activeTab, setActiveTab] = useState<DatasetDetailTab>('columns')
  const [previewLimit, setPreviewLimit] = useState<number>(20)
  const previewQuery = useDatasetPreview(datasetId, {
    limit: previewLimit,
    enabled: activeTab === 'preview',
  })
  const lineageQuery = useLineage(datasetId)
  const saveLineageMutation = useSaveLineage(datasetId)
  const [selectedColumn, setSelectedColumn] = useState<CatalogColumn | null>(null)
  const [previewSort, setPreviewSort] = useState<{
    key: string
    direction: PreviewSortDirection
  } | null>(null)
  const [expandedCells, setExpandedCells] = useState<Record<string, boolean>>({})

  if (datasetQuery.isPending) {
    return (
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Link to="/datasets">
            <Button variant="ghost" size="sm">
              ← 목록
            </Button>
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
            <Button variant="ghost" size="sm">
              ← 목록
            </Button>
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
  const preview = previewQuery.data?.data

  const sortedPreviewRows = useMemo(() => {
    const rows = preview?.rows ?? []
    if (!previewSort) {
      return rows
    }

    const nextRows = [...rows]
    nextRows.sort((left, right) => {
      const result = comparePreviewValues(left[previewSort.key], right[previewSort.key])
      return previewSort.direction === 'asc' ? result : -result
    })
    return nextRows
  }, [preview?.rows, previewSort])

  const onChangeTab = (nextTab: DatasetDetailTab) => {
    setActiveTab(nextTab)
    setSelectedColumn(null)
  }

  const onClickPreviewHeader = (columnName: string) => {
    setPreviewSort((prev) => {
      if (!prev || prev.key !== columnName) {
        return { key: columnName, direction: 'asc' }
      }

      return {
        key: columnName,
        direction: prev.direction === 'asc' ? 'desc' : 'asc',
      }
    })
  }

  const onChangePreviewLimit = (nextLimit: number) => {
    setPreviewLimit(nextLimit)
    setPreviewSort(null)
    setExpandedCells({})
  }

  const onTogglePreviewCell = (cellKey: string) => {
    setExpandedCells((prev) => ({
      ...prev,
      [cellKey]: !prev[cellKey],
    }))
  }

  const onNavigateDataset = (nextDatasetId: string) => {
    if (nextDatasetId === datasetId) {
      return
    }

    void navigate({ to: '/datasets/$datasetId', params: { datasetId: nextDatasetId } })
  }

  const onSaveLineage = async (nextGraph: LineageGraph) => {
    await saveLineageMutation.mutateAsync(nextGraph)
  }

  return (
    <section className="space-y-6">
      {/* Back navigation */}
      <div className="flex items-center gap-2">
        <Link to="/datasets">
          <Button variant="ghost" size="sm">
            ← 목록
          </Button>
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
              <Badge key={tag} variant="secondary">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Metadata grid */}
      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <MetaItem label="소유자" value={dataset.owner ?? '미지정'} />
          <MetaItem
            label="컬럼 수"
            value={columnsQuery.isPending ? '...' : String(columns.length)}
          />
          <MetaItem label="생성일" value={formatDate(dataset.created_at)} />
          <MetaItem label="수정일" value={formatDate(dataset.updated_at)} />
        </div>
      </Card>

      <Separator />

      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={activeTab === 'columns' ? 'default' : 'outline'}
            onClick={() => onChangeTab('columns')}
          >
            컬럼
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'preview' ? 'default' : 'outline'}
            onClick={() => onChangeTab('preview')}
          >
            Preview
          </Button>
          <Button
            size="sm"
            variant={activeTab === 'lineage' ? 'default' : 'outline'}
            onClick={() => onChangeTab('lineage')}
          >
            Lineage
          </Button>
        </div>

        {activeTab === 'columns' && (
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">컬럼 목록</h2>

            {columnsQuery.isPending ? (
              <div className="space-y-2">
                {['dataset-column-row-1', 'dataset-column-row-2', 'dataset-column-row-3'].map(
                  (key) => (
                    <div key={key} className="h-10 bg-[var(--muted)] animate-pulse rounded" />
                  ),
                )}
              </div>
            ) : columnsQuery.isError ? (
              <ErrorCard
                message="컬럼 정보를 불러올 수 없습니다."
                onRetry={() => columnsQuery.refetch()}
              />
            ) : columns.length === 0 ? (
              <EmptyState title="컬럼 정보가 없습니다." />
            ) : (
              <>
                <div className="hidden sm:block">
                  <ColumnTable columns={columns} onSelect={setSelectedColumn} />
                </div>
                <div className="block sm:hidden space-y-2">
                  {columns.map((col) => (
                    <ColumnCard key={col.column_name} column={col} onSelect={setSelectedColumn} />
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'preview' && (
          <div className="space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-semibold">데이터 프리뷰</h2>
              <label className="flex items-center gap-2 text-sm">
                <span className="text-[var(--muted-foreground)]">행 수</span>
                <select
                  aria-label="프리뷰 행 수"
                  className="h-9 rounded-md border bg-background px-2"
                  value={previewLimit}
                  onChange={(event) => onChangePreviewLimit(Number(event.target.value))}
                >
                  {PREVIEW_LIMIT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <p className="text-sm text-[var(--muted-foreground)]">
              최신 {previewLimit}건 기준 정렬
            </p>

            {previewQuery.isPending ? (
              <Card className="p-4 space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  {['preview-header-1', 'preview-header-2', 'preview-header-3'].map((key) => (
                    <div key={key} className="h-8 rounded bg-[var(--muted)] animate-pulse" />
                  ))}
                </div>
                {['preview-row-1', 'preview-row-2', 'preview-row-3'].map((key) => (
                  <div key={key} className="h-10 rounded bg-[var(--muted)] animate-pulse" />
                ))}
              </Card>
            ) : previewQuery.isError ? (
              <ErrorCard
                message="프리뷰 정보를 불러올 수 없습니다."
                onRetry={() => previewQuery.refetch()}
              />
            ) : (preview?.rows.length ?? 0) === 0 ? (
              preview?.meta.reason === 'dataset-not-mapped' ? (
                <EmptyState
                  title="프리뷰 준비중"
                  description="이 데이터셋은 아직 프리뷰 매핑이 준비되지 않았습니다."
                />
              ) : (
                <EmptyState
                  title="프리뷰 데이터가 없습니다."
                  description="소스 데이터가 비어 있어 표시할 행이 없습니다."
                />
              )
            ) : (
              <Card className="overflow-auto">
                <Table>
                  <THead>
                    <TR>
                      {preview?.columns.map((column) => {
                        const indicator =
                          previewSort?.key === column
                            ? previewSort.direction === 'asc'
                              ? ' ▲'
                              : ' ▼'
                            : ''
                        return (
                          <TH key={column}>
                            <button
                              type="button"
                              className="text-left text-sm font-medium"
                              onClick={() => onClickPreviewHeader(column)}
                            >
                              {column}
                              {indicator}
                            </button>
                          </TH>
                        )
                      })}
                    </TR>
                  </THead>
                  <TBody>
                    {sortedPreviewRows.map((row, rowIndex) => {
                      const rowKey = preview?.columns
                        .map((column) => formatPreviewValue(row[column]))
                        .join('|')

                      return (
                        <TR key={`preview-row-${rowKey}`}>
                          {preview?.columns.map((column) => {
                            const cellKey = `${rowIndex}:${column}`
                            const value = row[column]
                            const expandedValue = getExpandedJsonValue(value)
                            const isExpanded = Boolean(expandedCells[cellKey])

                            return (
                              <TD key={cellKey}>
                                {expandedValue ? (
                                  <div className="space-y-2">
                                    {isExpanded ? (
                                      <pre className="text-xs overflow-x-auto bg-[var(--muted)] p-2 rounded">
                                        <code>{JSON.stringify(expandedValue, null, 2)}</code>
                                      </pre>
                                    ) : (
                                      <code className="text-xs break-all">
                                        {JSON.stringify(expandedValue).slice(0, 120)}
                                        {JSON.stringify(expandedValue).length > 120 ? '...' : ''}
                                      </code>
                                    )}
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => onTogglePreviewCell(cellKey)}
                                    >
                                      {isExpanded ? '접기' : '펼치기'}
                                    </Button>
                                  </div>
                                ) : (
                                  <span className="text-sm">{formatPreviewValue(value)}</span>
                                )}
                              </TD>
                            )
                          })}
                        </TR>
                      )
                    })}
                  </TBody>
                </Table>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'lineage' && (
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">Lineage</h2>
            {lineageQuery.isPending ? (
              <div className="h-[60vh] rounded-md bg-[var(--muted)] animate-pulse" />
            ) : lineageQuery.isError ? (
              <ErrorCard
                message="리니지 정보를 불러올 수 없습니다."
                onRetry={() => lineageQuery.refetch()}
              />
            ) : lineageQuery.data?.data ? (
              <Card className="p-3">
                <LineageViewer
                  datasetId={datasetId}
                  graph={lineageQuery.data.data}
                  isSaving={saveLineageMutation.isPending}
                  onSave={onSaveLineage}
                  onNavigateDataset={onNavigateDataset}
                />
              </Card>
            ) : (
              <EmptyState title="리니지 정보가 없습니다." />
            )}
            {saveLineageMutation.isError && (
              <ErrorCard message={(saveLineageMutation.error as Error).message} />
            )}
          </div>
        )}
      </div>

      {/* Column detail side panel */}
      <ColumnDetailPanel column={selectedColumn} onClose={() => setSelectedColumn(null)} />
    </section>
  )
}
