import { apiGet } from '@/lib/api-client'
import type {
  ApiSuccess,
  DomainName,
  MarketplaceDomainDetail,
  MarketplaceDomainSummary,
  MarketplaceListingDetail,
  MarketplaceListingSummary,
} from '@pseudolab/shared-types'

export function getListings() {
  return apiGet<ApiSuccess<MarketplaceListingSummary[]>>('/marketplace/listings')
}

export function getListing(domain: DomainName, slug: string) {
  return apiGet<ApiSuccess<MarketplaceListingDetail>>(`/marketplace/listings/${domain}/${slug}`)
}

export function getMarketplaceDomains() {
  return apiGet<ApiSuccess<MarketplaceDomainSummary[]>>('/marketplace/domains')
}

export function getMarketplaceDomain(domain: DomainName) {
  return apiGet<ApiSuccess<MarketplaceDomainDetail>>(`/marketplace/domains/${domain}`)
}
