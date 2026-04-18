import { Input } from '@/components/ui/input'
import { useManifest } from '@/hooks/use-query-dashboard'
import type { AiManifestEntry } from '@pseudolab/shared-types'
import { ChevronDown, ChevronRight, Database, Search, ShieldAlert } from 'lucide-react'
import { useMemo, useState } from 'react'

type TableSidebarProps = {
  onTableClick?: (tableName: string) => void
}

export function TableSidebar({ onTableClick }: TableSidebarProps) {
  const { data, isPending } = useManifest()
  const [search, setSearch] = useState('')
  const [expandedDomains, setExpandedDomains] = useState<Set<string>>(new Set())

  const grouped = useMemo(() => {
    const entries = data?.data ?? []
    const filtered = search
      ? entries.filter(
          (e) =>
            e.name.toLowerCase().includes(search.toLowerCase()) ||
            e.dataset_id.toLowerCase().includes(search.toLowerCase()),
        )
      : entries

    const groups: Record<string, AiManifestEntry[]> = {}
    for (const entry of filtered) {
      const domain = entry.domain
      if (!groups[domain]) groups[domain] = []
      groups[domain].push(entry)
    }
    return groups
  }, [data, search])

  function toggleDomain(domain: string) {
    setExpandedDomains((prev) => {
      const next = new Set(prev)
      if (next.has(domain)) next.delete(domain)
      else next.add(domain)
      return next
    })
  }

  if (isPending) {
    return (
      <div className="space-y-2 p-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 animate-pulse rounded bg-[var(--muted)]" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] p-2">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--muted-foreground)]" />
          <Input
            placeholder="테이블 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 pl-7 text-xs"
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-1">
        {Object.entries(grouped).map(([domain, entries]) => (
          <div key={domain}>
            <button
              type="button"
              onClick={() => toggleDomain(domain)}
              className="flex w-full items-center gap-1 rounded px-2 py-1.5 text-xs font-semibold uppercase text-[var(--muted-foreground)] hover:bg-[var(--muted)]"
            >
              {expandedDomains.has(domain) ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              {domain}
              <span className="ml-auto text-[10px] font-normal">{entries.length}</span>
            </button>
            {expandedDomains.has(domain) && (
              <div className="ml-2 space-y-0.5">
                {entries.map((entry) => (
                  <button
                    key={entry.dataset_id}
                    type="button"
                    onClick={() => onTableClick?.(entry.table_name ?? entry.name)}
                    className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-xs hover:bg-[var(--muted)]"
                    title={entry.purpose ?? entry.name}
                  >
                    <Database className="h-3 w-3 shrink-0 text-[var(--muted-foreground)]" />
                    <span className="truncate">{entry.table_name ?? entry.name}</span>
                    {entry.has_pii && (
                      <ShieldAlert className="ml-auto h-3 w-3 shrink-0 text-amber-500" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {Object.keys(grouped).length === 0 && (
          <p className="p-3 text-center text-xs text-[var(--muted-foreground)]">
            테이블을 찾을 수 없습니다
          </p>
        )}
      </div>
    </div>
  )
}
