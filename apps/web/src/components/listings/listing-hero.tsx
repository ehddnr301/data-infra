import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { MarketplaceListingDetail } from '@pseudolab/shared-types'
import { ExternalLink } from 'lucide-react'

function formatDate(iso: string | null): string | null {
  if (!iso) {
    return null
  }

  return new Date(iso).toLocaleDateString('ko-KR')
}

export function ListingHero({ listing }: { listing: MarketplaceListingDetail }) {
  const verifiedLabel = formatDate(listing.last_verified_at)

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{listing.category}</Badge>
        <Badge variant="outline">{listing.domain}</Badge>
        {listing.preview_available && <Badge variant="outline">preview</Badge>}
        {listing.has_pii && <Badge variant="outline">PII</Badge>}
      </div>

      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">{listing.title}</h1>
        {listing.subtitle && (
          <p className="text-lg text-[var(--muted-foreground)]">{listing.subtitle}</p>
        )}
        <p className="max-w-3xl text-sm leading-6 text-[var(--muted-foreground)]">
          {listing.description}
        </p>
      </div>

      <div className="grid gap-3 text-sm text-[var(--muted-foreground)] md:grid-cols-3">
        <p>Owner: {listing.owner.display_name}</p>
        <p>업데이트 주기: {listing.update_frequency ?? '미정'}</p>
        <p>Coverage: {listing.coverage_summary ?? '정의되지 않음'}</p>
        <p>Dataset ID: {listing.dataset.id}</p>
        <p>
          Canonical route: /listings/{listing.domain}/{listing.slug}
        </p>
        <p>마지막 검증: {verifiedLabel ?? '미등록'}</p>
      </div>

      <div className="flex flex-wrap gap-2">
{listing.owner.contact_email && (
          <a href={`mailto:${listing.owner.contact_email}`}>
            <Button type="button" variant="outline" className="gap-2">
              <ExternalLink className="h-4 w-4" />
              Owner 연락
            </Button>
          </a>
        )}
      </div>
    </Card>
  )
}
