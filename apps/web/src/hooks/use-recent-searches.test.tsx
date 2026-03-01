import { RECENT_SEARCH_LIMIT, useRecentSearches } from '@/hooks/use-recent-searches'
import { act, renderHook } from '@testing-library/react'

describe('useRecentSearches', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('adds and deduplicates recent searches', () => {
    const { result } = renderHook(() => useRecentSearches())

    act(() => {
      result.current.addRecentSearch('search-one')
      result.current.addRecentSearch('search-two')
      result.current.addRecentSearch('search-one')
    })

    expect(result.current.recentSearches).toEqual(['search-one', 'search-two'])
  })

  it('does not store single-character or blank input', () => {
    const { result } = renderHook(() => useRecentSearches())

    act(() => {
      result.current.addRecentSearch(' ')
      result.current.addRecentSearch('a')
    })

    expect(result.current.recentSearches).toHaveLength(0)
    expect(window.localStorage.length).toBe(0)
  })

  it('keeps only the latest 10 searches', () => {
    const { result } = renderHook(() => useRecentSearches())

    act(() => {
      for (let i = 1; i <= RECENT_SEARCH_LIMIT + 2; i += 1) {
        result.current.addRecentSearch(`term-${i}`)
      }
    })

    expect(result.current.recentSearches).toHaveLength(RECENT_SEARCH_LIMIT)
    expect(result.current.recentSearches[0]).toBe('term-12')
    expect(result.current.recentSearches[9]).toBe('term-3')
  })
})
