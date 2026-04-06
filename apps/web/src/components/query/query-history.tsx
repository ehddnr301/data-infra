import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useQueryHistory } from '@/hooks/use-query-dashboard'
import { useAuth } from '@/lib/auth-context'
import { ChevronLeft, ChevronRight, Clock, History } from 'lucide-react'
import { useState } from 'react'

type QueryHistoryPanelProps = {
  onSelectQuery: (sql: string) => void
}

export function QueryHistoryPanel({ onSelectQuery }: QueryHistoryPanelProps) {
  const { auth } = useAuth()
  const [mode, setMode] = useState<'mine' | 'all'>('mine')
  const [page, setPage] = useState(1)

  const params = {
    user: mode === 'mine' ? auth?.email : undefined,
    page,
    pageSize: 10,
  }
  const { data, isPending } = useQueryHistory(params)

  const entries = data?.data ?? []
  const pagination = data?.pagination

  return (
    <Card className="space-y-3 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4" />
          <span className="text-sm font-semibold">쿼리 히스토리</span>
        </div>
        <div className="flex gap-1">
          <Button
            variant={mode === 'mine' ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setMode('mine')
              setPage(1)
            }}
          >
            내 쿼리
          </Button>
          <Button
            variant={mode === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setMode('all')
              setPage(1)
            }}
          >
            전체
          </Button>
        </div>
      </div>

      {isPending ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 animate-pulse rounded bg-[var(--muted)]" />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <p className="py-4 text-center text-sm text-[var(--muted-foreground)]">
          쿼리 히스토리가 없습니다
        </p>
      ) : (
        <div className="space-y-1">
          {entries.map((entry) => (
            <button
              key={entry.id}
              type="button"
              onClick={() => onSelectQuery(entry.executed_sql)}
              className="w-full rounded-md border border-[var(--border)] p-2 text-left hover:bg-[var(--muted)]"
            >
              <div className="flex items-center gap-2">
                <Badge
                  variant={entry.status === 'success' ? 'default' : 'destructive'}
                  className="text-[10px]"
                >
                  {entry.status === 'success' ? '성공' : '실패'}
                </Badge>
                {entry.execution_ms != null && (
                  <span className="flex items-center gap-0.5 text-[10px] text-[var(--muted-foreground)]">
                    <Clock className="h-2.5 w-2.5" />
                    {entry.execution_ms}ms
                  </span>
                )}
                {mode === 'all' && entry.user_name && (
                  <span className="ml-auto text-[10px] text-[var(--muted-foreground)]">
                    {entry.user_name}
                  </span>
                )}
              </div>
              <p className="mt-1 truncate font-mono text-xs text-[var(--foreground)]">
                {entry.executed_sql}
              </p>
              <p className="mt-0.5 text-[10px] text-[var(--muted-foreground)]">
                {formatRelativeTime(entry.created_at)}
              </p>
            </button>
          ))}
        </div>
      )}

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
    </Card>
  )
}

function formatRelativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '방금 전'
  if (minutes < 60) return `${minutes}분 전`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`
  const days = Math.floor(hours / 24)
  return `${days}일 전`
}
