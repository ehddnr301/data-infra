import { useEffect, useMemo, useState } from 'react'

const RECENT_SEARCH_KEY = 'catalog:search:recent:v1'
const RECENT_SEARCH_LIMIT = 10

function readRecentSearches(): string[] {
  try {
    const raw = window.localStorage.getItem(RECENT_SEARCH_KEY)
    if (!raw) {
      return []
    }

    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }

    return parsed.filter((value): value is string => typeof value === 'string')
  } catch {
    return []
  }
}

function writeRecentSearches(items: string[]): void {
  try {
    window.localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(items))
  } catch {
    return
  }
}

export function useRecentSearches() {
  const [recentSearches, setRecentSearches] = useState<string[]>([])

  useEffect(() => {
    setRecentSearches(readRecentSearches())
  }, [])

  const actions = useMemo(
    () => ({
      addRecentSearch: (value: string) => {
        const normalized = value.trim()
        if (normalized.length < 2) {
          return
        }

        setRecentSearches((previous) => {
          const deduped = [normalized, ...previous.filter((item) => item !== normalized)].slice(
            0,
            RECENT_SEARCH_LIMIT,
          )
          writeRecentSearches(deduped)
          return deduped
        })
      },
      removeRecentSearch: (value: string) => {
        setRecentSearches((previous) => {
          const next = previous.filter((item) => item !== value)
          writeRecentSearches(next)
          return next
        })
      },
      clearRecentSearches: () => {
        setRecentSearches([])
        writeRecentSearches([])
      },
    }),
    [],
  )

  return {
    recentSearches,
    ...actions,
  }
}

export { RECENT_SEARCH_KEY, RECENT_SEARCH_LIMIT }
