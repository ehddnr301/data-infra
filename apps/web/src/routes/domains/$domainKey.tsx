import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { ListingCard } from '@/components/listings/listing-card'
import { DatasetListSkeleton } from '@/components/skeleton/dataset-skeleton'
import { Card } from '@/components/ui/card'
import { useMarketplaceDomain } from '@/hooks/use-marketplace'
import { ApiError } from '@/lib/api-client'
import { normalizeDomainName } from '@pseudolab/shared-types'
import { Link, useParams } from '@tanstack/react-router'

export function DomainDetailPage() {
  const { domainKey } = useParams({ from: '/domains/$domainKey' })
  const domain = normalizeDomainName(domainKey)

  if (!domain) {
    return <ErrorCard message="지원하지 않는 domain hub입니다." />
  }

  const query = useMarketplaceDomain(domain)

  if (query.isPending) {
    return <DatasetListSkeleton />
  }

  if (query.isError) {
    const error = query.error as Error
    if (error instanceof ApiError && error.status === 404) {
      return <EmptyState title="도메인 허브를 찾을 수 없습니다." />
    }

    return <ErrorCard message={error.message} onRetry={query.refetch} />
  }

  const domainDetail = query.data?.data
  if (!domainDetail) {
    return <EmptyState title="도메인 데이터가 없습니다." />
  }

  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <Link to="/listings" className="text-sm text-[var(--muted-foreground)] hover:text-foreground">
          ← 전체 listings
        </Link>
        <h1 className="text-2xl font-semibold">{domainDetail.label} hub</h1>
        <p className="text-sm text-[var(--muted-foreground)]">{domainDetail.description}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <h2 className="text-sm text-[var(--muted-foreground)]">Listings</h2>
          <p className="mt-2 text-2xl font-semibold">{domainDetail.listing_count}</p>
        </Card>
        <Card>
          <h2 className="text-sm text-[var(--muted-foreground)]">Featured listing</h2>
          <p className="mt-2 text-lg font-semibold">{domainDetail.featured_listing_title ?? '미정'}</p>
        </Card>
        <Card>
          <h2 className="text-sm text-[var(--muted-foreground)]">Canonical base</h2>
          <p className="mt-2 text-lg font-semibold">/domains/{domainDetail.key}</p>
        </Card>
      </div>

      {domainDetail.listings.length === 0 ? (
        <EmptyState title="등록된 listing이 없습니다." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {domainDetail.listings.map((listing) => (
            <ListingCard key={listing.id} listing={listing} />
          ))}
        </div>
      )}
    </section>
  )
}
