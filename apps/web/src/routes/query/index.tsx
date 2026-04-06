import { DevLoginForm } from '@/components/auth/dev-login-form'
import { QueryHistoryPanel } from '@/components/query/query-history'
import { QueryError, QueryResults } from '@/components/query/query-results'
import { SqlEditor } from '@/components/query/sql-editor'
import { TableSidebar } from '@/components/query/table-sidebar'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useExecuteQuery, useManifest } from '@/hooks/use-query-dashboard'
import { ApiError } from '@/lib/api-client'
import { useAuth } from '@/lib/auth-context'
import { LogOut, Play, Terminal } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'

export function QueryDashboardPage() {
  const { isAuthenticated, auth, logout } = useAuth()
  const [sqlValue, setSqlValue] = useState('')
  const mutation = useExecuteQuery()
  const { data: manifestData } = useManifest()

  const schema = useMemo(() => {
    if (!manifestData?.data) return undefined
    const s: Record<string, string[]> = {}
    for (const entry of manifestData.data) {
      s[entry.name] = []
    }
    return s
  }, [manifestData])

  const handleExecute = useCallback(() => {
    const trimmed = sqlValue.trim()
    if (trimmed) {
      mutation.mutate(trimmed)
    }
  }, [sqlValue, mutation])

  const handleTableClick = useCallback(
    (tableName: string) => {
      const current = sqlValue.trim()
      if (!current) {
        setSqlValue(`SELECT * FROM ${tableName} LIMIT 10`)
      } else {
        setSqlValue((prev) => `${prev} ${tableName}`)
      }
    },
    [sqlValue],
  )

  if (!isAuthenticated) {
    return <DevLoginForm />
  }

  const result = mutation.data
  const error = mutation.error

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="h-5 w-5" />
          <h1 className="text-lg font-bold">SQL 쿼리 대시보드</h1>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--muted-foreground)]">{auth?.email}</span>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        {/* Left: Table sidebar */}
        <Card className="hidden h-[calc(100vh-12rem)] overflow-hidden lg:block">
          <TableSidebar onTableClick={handleTableClick} />
        </Card>

        {/* Right: Editor + Results + History */}
        <div className="space-y-4">
          {/* SQL Editor */}
          <div className="space-y-2">
            <SqlEditor
              value={sqlValue}
              onChange={setSqlValue}
              onExecute={handleExecute}
              schema={schema}
            />
            <div className="flex items-center gap-2">
              <Button onClick={handleExecute} disabled={mutation.isPending || !sqlValue.trim()}>
                <Play className="mr-1 h-4 w-4" />
                {mutation.isPending ? '실행 중...' : '실행'}
              </Button>
              <span className="text-xs text-[var(--muted-foreground)]">Ctrl+Enter로 실행</span>
            </div>
          </div>

          {/* Results */}
          {result && (
            <QueryResults
              columns={result.data.columns}
              rows={result.data.rows}
              rowCount={result.data.row_count}
              truncated={result.data.truncated}
              executionMs={result.meta.execution_ms}
              executedSql={result.data.executed_sql}
            />
          )}

          {error && (
            <QueryError
              error={
                error instanceof ApiError && error.body ? error.body : { message: error.message }
              }
            />
          )}

          {/* History */}
          <QueryHistoryPanel onSelectQuery={setSqlValue} />
        </div>
      </div>
    </section>
  )
}
