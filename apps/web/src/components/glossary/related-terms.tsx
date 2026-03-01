import { Input } from '@/components/ui/input'
import type { GlossaryTerm } from '@pseudolab/shared-types'
import { useMemo, useState } from 'react'

type RelatedTermsProps = {
  terms: GlossaryTerm[]
  selectedIds: string[]
  onChange: (nextIds: string[]) => void
  excludeId?: string
}

export function RelatedTermsSelector({
  terms,
  selectedIds,
  onChange,
  excludeId,
}: RelatedTermsProps) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const source = terms.filter((term) => term.id !== excludeId)
    if (!query.trim()) {
      return source
    }

    const normalized = query.toLowerCase()
    return source.filter((term) => {
      return (
        term.term.toLowerCase().includes(normalized) ||
        term.definition.toLowerCase().includes(normalized)
      )
    })
  }, [excludeId, query, terms])

  return (
    <div className="space-y-2">
      <Input
        placeholder="관련 용어 검색"
        value={query}
        onChange={(event) => setQuery((event.target as HTMLInputElement).value)}
      />
      <div className="max-h-52 overflow-auto rounded-md border border-[var(--border)] p-2 space-y-1">
        {filtered.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">선택 가능한 용어가 없습니다.</p>
        ) : (
          filtered.map((item) => {
            const checked = selectedIds.includes(item.id)
            return (
              <label
                key={item.id}
                className="flex items-start gap-2 rounded px-1 py-1 hover:bg-[var(--muted)]/50"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => {
                    if (event.target.checked) {
                      onChange([...selectedIds, item.id])
                      return
                    }

                    onChange(selectedIds.filter((id) => id !== item.id))
                  }}
                />
                <span className="min-w-0 text-sm">
                  <span className="font-medium">{item.term}</span>
                  <span className="ml-2 text-xs text-[var(--muted-foreground)]">
                    {item.definition}
                  </span>
                </span>
              </label>
            )
          })
        )}
      </div>
    </div>
  )
}
