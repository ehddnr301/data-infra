import {
  getListing,
  getListings,
  getMarketplaceDomain,
  getMarketplaceDomains,
} from '@/api/marketplace'
import type { DomainName } from '@pseudolab/shared-types'
import { useQuery } from '@tanstack/react-query'

export function useListings() {
  return useQuery({
    queryKey: ['marketplace', 'listings'],
    queryFn: () => getListings(),
  })
}

export function useListing(domain: DomainName, slug: string) {
  return useQuery({
    queryKey: ['marketplace', 'listing', domain, slug],
    queryFn: () => getListing(domain, slug),
    enabled: Boolean(domain) && Boolean(slug),
  })
}

export function useMarketplaceDomains() {
  return useQuery({
    queryKey: ['marketplace', 'domains'],
    queryFn: () => getMarketplaceDomains(),
  })
}

export function useMarketplaceDomain(domain: DomainName) {
  return useQuery({
    queryKey: ['marketplace', 'domain', domain],
    queryFn: () => getMarketplaceDomain(domain),
    enabled: Boolean(domain),
  })
}
