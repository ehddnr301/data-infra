import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { MarketplaceListingSummary } from '@pseudolab/shared-types'
import { Link } from '@tanstack/react-router'

function formatDate(iso: string | null): string | null {
  if (!iso) {
    return null
  }

  return new Date(iso).toLocaleDateString('ko-KR')
}

export function ListingCard({ listing }: { listing: MarketplaceListingSummary }) {
  const verifiedLabel = formatDate(listing.last_verified_at)

  return (
    <Link
      to="/listings/$domain/$listingSlug"
      params={{ domain: listing.domain, listingSlug: listing.slug }}
      className="block"
    >
      <article data-testid="listing-card">
        <Card className="h-full space-y-3 transition-colors hover:border-[var(--primary)]">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{listing.category}</Badge>
            <Badge variant="outline">{listing.domain}</Badge>
            {listing.preview_available && <Badge variant="outline">preview</Badge>}
            {listing.has_pii && <Badge variant="outline">PII</Badge>}
          </div>

          <div className="space-y-1">
            <h2 className="text-lg font-semibold">{listing.title}</h2>
            {listing.subtitle && (
              <p className="text-sm text-[var(--muted-foreground)]">{listing.subtitle}</p>
            )}
          </div>

          <p className="text-sm text-[var(--muted-foreground)]">{listing.description}</p>

          <div className="grid gap-2 text-xs text-[var(--muted-foreground)] sm:grid-cols-2">
            <p>Owner: {listing.owner.display_name}</p>
            <p>업데이트 주기: {listing.update_frequency ?? '미정'}</p>
            <p>Dataset: {listing.dataset_id}</p>
            {verifiedLabel && <p>마지막 검증: {verifiedLabel}</p>}
          </div>

          {listing.business_need_tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {listing.business_need_tags.map((tag) => (
                <Badge key={`${listing.id}:${tag}`} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </Card>
      </article>
    </Link>
  )
}
