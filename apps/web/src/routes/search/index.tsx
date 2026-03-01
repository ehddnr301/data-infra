import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { HighlightText } from '@/components/search/highlight-text'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useRecentSearches } from '@/hooks/use-recent-searches'
import { useIntegratedSearch } from '@/hooks/use-search'
import type { DomainName, SearchType } from '@pseudolab/shared-types'
import { Link } from '@tanstack/react-router'
import { useEffect, useMemo, useRef } from 'react'

const SEARCH_TYPES: SearchType[] = ['all', 'dataset', 'column', 'glossary']
const DOMAINS: Array<{ label: string; value?: DomainName }> = [
  { label: '전체' },
  { label: 'github', value: 'github' },
  { label: 'discord', value: 'discord' },
  { label: 'linkedin', value: 'linkedin' },
  { label: 'members', value: 'members' },
]

function parseSearchType(value: string | null): SearchType {
  if (value === 'dataset' || value === 'column' || value === 'glossary') {
    return value
  }
  return 'all'
}

function parseDomain(value: string | null): DomainName | undefined {
  if (value === 'github' || value === 'discord' || value === 'linkedin' || value === 'members') {
    return value
  }
  return undefined
}

function parsePositiveInt(value: string | null, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return fallback
  }
  return parsed
}

function buildSearchHref(params: {
  q: string
  type: SearchType
  domain?: DomainName
  page?: number
  pageSize?: number
}): string {
  const searchParams = new URLSearchParams()
  searchParams.set('q', params.q)
  searchParams.set('type', params.type)
  if (params.domain) {
    searchParams.set('domain', params.domain)
  }
  if (params.type !== 'all') {
    searchParams.set('page', String(params.page ?? 1))
    searchParams.set('pageSize', String(params.pageSize ?? 20))
  }
  return `/search?${searchParams.toString()}`
}

export function SearchPage() {
  const resultRef = useRef<HTMLElement | null>(null)
  const { recentSearches, addRecentSearch, removeRecentSearch, clearRecentSearches } =
    useRecentSearches()

  const params = new URLSearchParams(window.location.search)
  const current = {
    q: (params.get('q') ?? '').trim(),
    type: parseSearchType(params.get('type')),
    domain: parseDomain(params.get('domain')),
    page: parsePositiveInt(params.get('page'), 1),
    pageSize: parsePositiveInt(params.get('pageSize'), 20),
  }

  const query = useIntegratedSearch({
    q: current.q,
    type: current.type,
    domain: current.domain,
    page: current.type === 'all' ? 1 : current.page,
    pageSize: current.type === 'all' ? 5 : current.pageSize,
  })

  const selectedGroup =
    query.data?.data.groups[
      current.type === 'dataset' ? 'datasets' : current.type === 'column' ? 'columns' : 'glossary'
    ]

  const totalPages = useMemo(() => {
    if (current.type === 'all') {
      return 1
    }
    const total = selectedGroup?.total ?? 0
    return Math.max(1, Math.ceil(total / current.pageSize))
  }, [current.pageSize, current.type, selectedGroup?.total])

  useEffect(() => {
    if (!current.q || query.isPending) {
      return
    }
    resultRef.current?.focus()
  }, [current.q, query.isPending])

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">통합 검색</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          dataset, column, glossary를 한 번에 검색합니다.
        </p>
      </div>

      <Card>
        <form
          aria-label="통합 검색"
          action="/search"
          method="get"
          className="space-y-3"
          onSubmit={(event) => {
            const formData = new FormData(event.currentTarget)
            const q = String(formData.get('q') ?? '').trim()
            addRecentSearch(q)
          }}
        >
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              name="q"
              type="search"
              placeholder="검색어를 입력하세요"
              defaultValue={current.q}
              className="sm:flex-1"
            />
            <select
              name="domain"
              defaultValue={current.domain ?? ''}
              className="h-9 rounded-md border border-[var(--border)] bg-white px-3 text-sm"
              aria-label="도메인 필터"
            >
              {DOMAINS.map((domain) => (
                <option key={domain.label} value={domain.value ?? ''}>
                  {domain.label}
                </option>
              ))}
            </select>
            <input type="hidden" name="type" value={current.type} />
            {current.type !== 'all' ? (
              <input type="hidden" name="pageSize" value={String(current.pageSize)} />
            ) : null}
            <Button type="submit">검색</Button>
          </div>

          {recentSearches.length > 0 ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-[var(--muted-foreground)]">최근 검색어</p>
                <Button size="sm" variant="ghost" type="button" onClick={clearRecentSearches}>
                  전체 삭제
                </Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {recentSearches.map((item) => (
                  <div
                    key={item}
                    className="inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs"
                  >
                    <a
                      href={buildSearchHref({
                        q: item,
                        type: current.type,
                        domain: current.domain,
                      })}
                      className="hover:underline"
                      onClick={() => addRecentSearch(item)}
                    >
                      {item}
                    </a>
                    <button
                      type="button"
                      className="text-[var(--muted-foreground)]"
                      onClick={() => removeRecentSearch(item)}
                      aria-label={`${item} 삭제`}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </form>
      </Card>

      <div className="flex flex-wrap gap-2">
        {SEARCH_TYPES.map((type) => (
          <a
            key={type}
            href={buildSearchHref({
              q: current.q,
              type,
              domain: current.domain,
              page: 1,
              pageSize: current.pageSize,
            })}
          >
            <Button size="sm" variant={current.type === type ? 'default' : 'outline'}>
              {type}
            </Button>
          </a>
        ))}
      </div>

      {!current.q ? (
        <EmptyState
          title="검색어를 입력하세요."
          description="검색어를 입력하면 통합 결과가 표시됩니다."
        />
      ) : null}

      {current.q && query.isPending ? (
        <Card className="space-y-2">
          {['s1', 's2', 's3', 's4', 's5'].map((key) => (
            <div key={key} className="h-8 rounded bg-[var(--muted)] animate-pulse" />
          ))}
        </Card>
      ) : null}

      {current.q && query.isError ? (
        <ErrorCard
          message={(query.error as Error).message || '검색 중 오류가 발생했습니다.'}
          onRetry={() => query.refetch()}
        />
      ) : null}

      {current.q && !query.isPending && !query.isError ? (
        <section ref={resultRef} tabIndex={-1} className="space-y-4 outline-none">
          {current.type === 'all' ? (
            <div className="space-y-3">
              <Card className="space-y-2">
                <h2 className="font-medium">
                  datasets ({query.data?.data.groups.datasets.total ?? 0})
                </h2>
                {(query.data?.data.groups.datasets.items ?? []).length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">결과 없음</p>
                ) : (
                  (query.data?.data.groups.datasets.items ?? []).map((item) => (
                    <Link
                      key={item.id}
                      to="/datasets/$datasetId"
                      params={{ datasetId: item.id }}
                      className="block rounded border p-3 hover:border-[var(--primary)]"
                    >
                      <p className="font-medium">
                        <HighlightText text={item.name} keyword={current.q} />
                      </p>
                      <p className="text-sm text-[var(--muted-foreground)]">
                        <HighlightText text={item.description} keyword={current.q} />
                      </p>
                    </Link>
                  ))
                )}
              </Card>

              <Card className="space-y-2">
                <h2 className="font-medium">
                  columns ({query.data?.data.groups.columns.total ?? 0})
                </h2>
                {(query.data?.data.groups.columns.items ?? []).length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">결과 없음</p>
                ) : (
                  (query.data?.data.groups.columns.items ?? []).map((item) => (
                    <Link
                      key={`${item.dataset_id}:${item.column_name}`}
                      to="/datasets/$datasetId"
                      params={{ datasetId: item.dataset_id }}
                      className="block rounded border p-3 hover:border-[var(--primary)]"
                    >
                      <p className="font-medium">
                        {item.dataset_name} /{' '}
                        <HighlightText text={item.column_name} keyword={current.q} />
                      </p>
                      <p className="text-sm text-[var(--muted-foreground)]">
                        <HighlightText text={item.description ?? ''} keyword={current.q} />
                      </p>
                    </Link>
                  ))
                )}
              </Card>

              <Card className="space-y-2">
                <h2 className="font-medium">
                  glossary ({query.data?.data.groups.glossary.total ?? 0})
                </h2>
                {(query.data?.data.groups.glossary.items ?? []).length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">결과 없음</p>
                ) : (
                  (query.data?.data.groups.glossary.items ?? []).map((item) => (
                    <Link
                      key={item.id}
                      to="/glossary/$termId"
                      params={{ termId: item.id }}
                      className="block rounded border p-3 hover:border-[var(--primary)]"
                    >
                      <p className="font-medium">
                        <HighlightText text={item.term} keyword={current.q} />
                      </p>
                      <p className="text-sm text-[var(--muted-foreground)]">
                        <HighlightText text={item.definition} keyword={current.q} />
                      </p>
                    </Link>
                  ))
                )}
              </Card>
            </div>
          ) : null}

          {current.type === 'dataset' ? (
            <Card className="space-y-2">
              <h2 className="font-medium">
                datasets ({query.data?.data.groups.datasets.total ?? 0})
              </h2>
              {(query.data?.data.groups.datasets.items ?? []).length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">결과 없음</p>
              ) : (
                (query.data?.data.groups.datasets.items ?? []).map((item) => (
                  <Link
                    key={item.id}
                    to="/datasets/$datasetId"
                    params={{ datasetId: item.id }}
                    className="block rounded border p-3 hover:border-[var(--primary)]"
                  >
                    <p className="font-medium">
                      <HighlightText text={item.name} keyword={current.q} />
                    </p>
                    <p className="text-sm text-[var(--muted-foreground)]">
                      <HighlightText text={item.description} keyword={current.q} />
                    </p>
                  </Link>
                ))
              )}
            </Card>
          ) : null}

          {current.type === 'column' ? (
            <Card className="space-y-2">
              <h2 className="font-medium">
                columns ({query.data?.data.groups.columns.total ?? 0})
              </h2>
              {(query.data?.data.groups.columns.items ?? []).length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">결과 없음</p>
              ) : (
                (query.data?.data.groups.columns.items ?? []).map((item) => (
                  <Link
                    key={`${item.dataset_id}:${item.column_name}`}
                    to="/datasets/$datasetId"
                    params={{ datasetId: item.dataset_id }}
                    className="block rounded border p-3 hover:border-[var(--primary)]"
                  >
                    <p className="font-medium">
                      {item.dataset_name} /{' '}
                      <HighlightText text={item.column_name} keyword={current.q} />
                    </p>
                    <p className="text-sm text-[var(--muted-foreground)]">
                      <HighlightText text={item.description ?? ''} keyword={current.q} />
                    </p>
                  </Link>
                ))
              )}
            </Card>
          ) : null}

          {current.type === 'glossary' ? (
            <Card className="space-y-2">
              <h2 className="font-medium">
                glossary ({query.data?.data.groups.glossary.total ?? 0})
              </h2>
              {(query.data?.data.groups.glossary.items ?? []).length === 0 ? (
                <p className="text-sm text-[var(--muted-foreground)]">결과 없음</p>
              ) : (
                (query.data?.data.groups.glossary.items ?? []).map((item) => (
                  <Link
                    key={item.id}
                    to="/glossary/$termId"
                    params={{ termId: item.id }}
                    className="block rounded border p-3 hover:border-[var(--primary)]"
                  >
                    <p className="font-medium">
                      <HighlightText text={item.term} keyword={current.q} />
                    </p>
                    <p className="text-sm text-[var(--muted-foreground)]">
                      <HighlightText text={item.definition} keyword={current.q} />
                    </p>
                  </Link>
                ))
              )}
            </Card>
          ) : null}

          {current.type !== 'all' ? (
            <div className="flex items-center justify-end gap-2">
              <a
                href={buildSearchHref({
                  q: current.q,
                  type: current.type,
                  domain: current.domain,
                  page: Math.max(1, current.page - 1),
                  pageSize: current.pageSize,
                })}
              >
                <Button variant="outline" size="sm" disabled={current.page <= 1}>
                  이전
                </Button>
              </a>
              <p className="text-sm text-[var(--muted-foreground)]">
                {current.page} / {totalPages}
              </p>
              <a
                href={buildSearchHref({
                  q: current.q,
                  type: current.type,
                  domain: current.domain,
                  page: Math.min(totalPages, current.page + 1),
                  pageSize: current.pageSize,
                })}
              >
                <Button variant="outline" size="sm" disabled={current.page >= totalPages}>
                  다음
                </Button>
              </a>
            </div>
          ) : null}
        </section>
      ) : null}
    </section>
  )
}
