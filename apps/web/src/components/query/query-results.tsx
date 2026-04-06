import { EmptyState } from '@/components/empty-state'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table'
import { AlertCircle, Clock } from 'lucide-react'

type QueryResultsProps = {
  columns: string[]
  rows: Record<string, unknown>[]
  rowCount: number
  truncated: boolean
  executionMs: number
  executedSql: string
}

type QueryErrorProps = {
  error: { type?: string; title?: string; detail?: string; message?: string }
}

export function QueryResults({
  columns,
  rows,
  rowCount,
  truncated,
  executionMs,
}: QueryResultsProps) {
  if (columns.length === 0) {
    return <EmptyState title="결과 없음" description="쿼리가 결과를 반환하지 않았습니다." />
  }

  return (
    <Card className="space-y-3 p-4">
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium">{rowCount}행 반환</span>
        <span className="flex items-center gap-1 text-[var(--muted-foreground)]">
          <Clock className="h-3 w-3" />
          {executionMs}ms
        </span>
        {truncated && (
          <Badge variant="outline" className="text-amber-600">
            100행 제한
          </Badge>
        )}
      </div>
      <div className="overflow-x-auto rounded-md border border-[var(--border)]">
        <Table>
          <THead>
            <TR>
              {columns.map((col) => (
                <TH key={col} className="whitespace-nowrap text-xs">
                  {col}
                </TH>
              ))}
            </TR>
          </THead>
          <TBody>
            {rows.map((row, i) => (
              <TR key={`row-${JSON.stringify(Object.values(row).slice(0, 3))}-${i}`}>
                {columns.map((col) => (
                  <TD key={col} className="max-w-[300px] truncate whitespace-nowrap text-xs">
                    {formatCell(row[col])}
                  </TD>
                ))}
              </TR>
            ))}
          </TBody>
        </Table>
      </div>
    </Card>
  )
}

export function QueryError({ error }: QueryErrorProps) {
  return (
    <Card className="flex items-start gap-3 border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950">
      <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
      <div className="space-y-1">
        <p className="text-sm font-medium text-red-700 dark:text-red-400">
          {error.title ?? '쿼리 오류'}
        </p>
        <p className="text-xs text-red-600 dark:text-red-300">
          {error.detail ?? error.message ?? '알 수 없는 오류가 발생했습니다.'}
        </p>
      </div>
    </Card>
  )
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return 'NULL'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
