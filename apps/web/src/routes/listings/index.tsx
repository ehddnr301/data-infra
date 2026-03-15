import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { ListingCard } from '@/components/listings/listing-card'
import { DatasetListSkeleton } from '@/components/skeleton/dataset-skeleton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useListings } from '@/hooks/use-marketplace'
import type { MarketplaceListingSummary } from '@pseudolab/shared-types'
import { useMemo, useState } from 'react'

function sortListings(
  listings: MarketplaceListingSummary[],
  sort: 'recent' | 'name',
): MarketplaceListingSummary[] {
  return [...listings].sort((left, right) => {
    if (sort === 'name') {
      return left.title.localeCompare(right.title, 'ko-KR')
    }

    return (right.last_verified_at ?? right.id).localeCompare(
      left.last_verified_at ?? left.id,
      'ko-KR',
    )
  })
}

export function ListingsPage() {
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [domainFilter, setDomainFilter] = useState<string>('all')
  const [businessNeedFilter, setBusinessNeedFilter] = useState<string>('all')
  const [sort, setSort] = useState<'recent' | 'name'>('recent')
  const { data, isPending, isError, error, refetch } = useListings()

  const listings = data?.data ?? []

  const categories = useMemo(
    () => ['all', ...Array.from(new Set(listings.map((listing) => listing.category)))],
    [listings],
  )
  const domains = useMemo(
    () => ['all', ...Array.from(new Set(listings.map((listing) => listing.domain)))],
    [listings],
  )
  const businessNeeds = useMemo(
    () => [
      'all',
      ...Array.from(new Set(listings.flatMap((listing) => listing.business_need_tags))),
    ],
    [listings],
  )

  const filteredListings = useMemo(() => {
    const loweredSearch = search.trim().toLowerCase()

    return sortListings(
      listings.filter((listing) => {
        const matchesSearch =
          loweredSearch.length === 0 ||
          listing.title.toLowerCase().includes(loweredSearch) ||
          listing.description.toLowerCase().includes(loweredSearch) ||
          (listing.subtitle ?? '').toLowerCase().includes(loweredSearch) ||
          listing.dataset_id.toLowerCase().includes(loweredSearch)

        const matchesCategory = categoryFilter === 'all' || listing.category === categoryFilter
        const matchesDomain = domainFilter === 'all' || listing.domain === domainFilter
        const matchesBusinessNeed =
          businessNeedFilter === 'all' || listing.business_need_tags.includes(businessNeedFilter)

        return matchesSearch && matchesCategory && matchesDomain && matchesBusinessNeed
      }),
      sort,
    )
  }, [businessNeedFilter, categoryFilter, domainFilter, listings, search, sort])

  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Marketplace listings</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Dataset-first marketplace surface. 각 dataset product는 canonical listing detail로
          연결됩니다.
        </p>
      </div>

      <div className="grid gap-3 rounded-lg border border-[var(--border)] bg-white p-4 md:grid-cols-2 xl:grid-cols-5">
        <Input
          placeholder="제목, 설명, dataset id 검색"
          value={search}
          onChange={(event) => setSearch((event.target as HTMLInputElement).value)}
        />

        <select
          aria-label="카테고리 필터"
          className="h-9 rounded-md border border-[var(--border)] bg-white px-3 text-sm"
          value={categoryFilter}
          onChange={(event) => setCategoryFilter(event.target.value)}
        >
          {categories.map((category) => (
            <option key={category} value={category}>
              {category === 'all' ? '전체 카테고리' : category}
            </option>
          ))}
        </select>

        <select
          aria-label="도메인 필터"
          className="h-9 rounded-md border border-[var(--border)] bg-white px-3 text-sm"
          value={domainFilter}
          onChange={(event) => setDomainFilter(event.target.value)}
        >
          {domains.map((domain) => (
            <option key={domain} value={domain}>
              {domain === 'all' ? '전체 도메인' : domain}
            </option>
          ))}
        </select>

        <select
          aria-label="비즈니스 니즈 필터"
          className="h-9 rounded-md border border-[var(--border)] bg-white px-3 text-sm"
          value={businessNeedFilter}
          onChange={(event) => setBusinessNeedFilter(event.target.value)}
        >
          {businessNeeds.map((need) => (
            <option key={need} value={need}>
              {need === 'all' ? '전체 business need' : need}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <select
            aria-label="정렬"
            className="h-9 flex-1 rounded-md border border-[var(--border)] bg-white px-3 text-sm"
            value={sort}
            onChange={(event) => setSort(event.target.value as 'recent' | 'name')}
          >
            <option value="recent">최근 업데이트순</option>
            <option value="name">이름순</option>
          </select>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setSearch('')
              setCategoryFilter('all')
              setDomainFilter('all')
              setBusinessNeedFilter('all')
              setSort('recent')
            }}
          >
            초기화
          </Button>
        </div>
      </div>

      {isPending && <DatasetListSkeleton />}
      {isError && (
        <ErrorCard
          message={(error as Error).message || '리스팅을 불러오는 중 오류가 발생했습니다.'}
          onRetry={refetch}
        />
      )}

      {!isPending && !isError && filteredListings.length === 0 && (
        <EmptyState
          title="등록된 listing이 없습니다."
          description="필터를 초기화하거나 다른 검색어를 시도해 보세요."
        />
      )}

      {!isPending && !isError && filteredListings.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filteredListings.map((listing) => (
            <ListingCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}
    </section>
  )
}
