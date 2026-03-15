import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { LineageViewer } from '@/components/lineage/lineage-viewer'
import { ListingBusinessNeeds } from '@/components/listings/listing-business-needs'
import { ListingCard } from '@/components/listings/listing-card'
import { ListingHero } from '@/components/listings/listing-hero'
import { ListingOwnerPanel } from '@/components/listings/listing-owner-panel'
import { ListingResourceList } from '@/components/listings/listing-resource-list'
import { DatasetDetailSkeleton } from '@/components/skeleton/dataset-skeleton'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table'
import { useColumns, useDatasetPreview } from '@/hooks/use-catalog'
import { useLineage } from '@/hooks/use-lineage'
import { useListing } from '@/hooks/use-marketplace'
import { ApiError } from '@/lib/api-client'
import { getMarketplaceListingRouteParams, normalizeDomainName } from '@pseudolab/shared-types'
import { Link, useNavigate, useParams } from '@tanstack/react-router'

function formatPreviewValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '-'
  }

  if (typeof value === 'string') {
    return value
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }

  return JSON.stringify(value)
}

export function ListingDetailPage() {
  const navigate = useNavigate()
  const { domain, listingSlug } = useParams({ from: '/listings/$domain/$listingSlug' })
  const normalizedDomain = normalizeDomainName(domain)

  if (!normalizedDomain) {
    return <ErrorCard message="지원하지 않는 listing domain입니다." />
  }

  const listingQuery = useListing(normalizedDomain, listingSlug)
  const listing = listingQuery.data?.data
  const datasetId = listing?.dataset.id ?? ''
  const columnsQuery = useColumns(datasetId)
  const previewQuery = useDatasetPreview(datasetId, { limit: 10, enabled: Boolean(datasetId) })
  const lineageQuery = useLineage(datasetId)

  const handleNavigateDataset = (nextDatasetId: string) => {
    const inferredDomain = normalizeDomainName(nextDatasetId.split('.')[0] ?? '') ?? listing?.domain
    if (!inferredDomain) {
      return
    }

    const params = getMarketplaceListingRouteParams({
      datasetId: nextDatasetId,
      domain: inferredDomain,
    })

    void navigate({
      to: '/listings/$domain/$listingSlug',
      params: {
        domain: params.domain,
        listingSlug: params.listingSlug,
      },
    })
  }

  if (listingQuery.isPending) {
    return <DatasetDetailSkeleton />
  }

  if (listingQuery.isError) {
    const error = listingQuery.error as Error
    if (error instanceof ApiError && error.status === 404) {
      return (
        <Card className="space-y-3">
          <h1 className="text-xl font-semibold">리스팅을 찾을 수 없습니다.</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            목록으로 돌아가 다른 리스팅을 확인해 보세요.
          </p>
          <Link to="/listings">
            <Button type="button" variant="outline">
              목록으로 이동
            </Button>
          </Link>
        </Card>
      )
    }

    return (
      <ErrorCard
        message={error.message || '리스팅을 불러오는 중 오류가 발생했습니다.'}
        onRetry={listingQuery.refetch}
      />
    )
  }

  if (!listing) {
    return <EmptyState title="리스팅 데이터가 없습니다." />
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center gap-2">
        <Link to="/listings">
          <Button type="button" variant="outline" size="sm">
            ← 목록
          </Button>
        </Link>
        <Link
          to="/domains/$domainKey"
          params={{ domainKey: listing.domain }}
          className="text-sm text-[var(--muted-foreground)] hover:text-foreground"
        >
          {listing.domain} hub 보기
        </Link>
      </div>

      <ListingHero listing={listing} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_360px]">
        <div className="space-y-6">
          <Card className="space-y-4">
            <div className="space-y-2">
              <h2 className="text-lg font-semibold">Dataset overview</h2>
              <p className="text-sm leading-6 text-[var(--muted-foreground)]">
                {listing.dataset.description}
              </p>
            </div>

            {listing.dataset.purpose && (
              <div className="space-y-2">
                <h3 className="font-medium">Purpose</h3>
                <p className="text-sm text-[var(--muted-foreground)]">{listing.dataset.purpose}</p>
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <h3 className="font-medium">Limitations</h3>
                {listing.dataset.limitations.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted-foreground)]">
                    {listing.dataset.limitations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">
                    제한사항이 등록되지 않았습니다.
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <h3 className="font-medium">Usage examples</h3>
                {listing.dataset.usage_examples.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted-foreground)]">
                    {listing.dataset.usage_examples.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">
                    사용 예시가 등록되지 않았습니다.
                  </p>
                )}
              </div>
            </div>

            {listing.dataset.tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {listing.dataset.tags.map((tag) => (
                  <Badge key={`${listing.id}:${tag}`} variant="outline">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </Card>

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Preview</h2>
            {previewQuery.isPending ? (
              <div className="h-24 animate-pulse rounded bg-[var(--muted)]" />
            ) : previewQuery.isError ? (
              <ErrorCard
                message={(previewQuery.error as Error).message}
                onRetry={previewQuery.refetch}
              />
            ) : previewQuery.data?.data.rows.length ? (
              <Table>
                <THead>
                  <TR>
                    {previewQuery.data.data.columns.map((column) => (
                      <TH key={column}>{column}</TH>
                    ))}
                  </TR>
                </THead>
                <TBody>
                  {previewQuery.data.data.rows.slice(0, 5).map((row, index) => (
                    <TR key={`${listing.dataset.id}:preview:${index}`}>
                      {previewQuery.data?.data.columns.map((column) => (
                        <TD key={`${listing.dataset.id}:${index}:${column}`}>
                          {formatPreviewValue(row[column])}
                        </TD>
                      ))}
                    </TR>
                  ))}
                </TBody>
              </Table>
            ) : (
              <EmptyState
                title="프리뷰 데이터가 없습니다."
                description="연결된 preview source가 없거나 비어 있습니다."
              />
            )}
          </Card>

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Columns</h2>
            {columnsQuery.isPending ? (
              <div className="h-24 animate-pulse rounded bg-[var(--muted)]" />
            ) : columnsQuery.isError ? (
              <ErrorCard
                message={(columnsQuery.error as Error).message}
                onRetry={columnsQuery.refetch}
              />
            ) : columnsQuery.data?.data.length ? (
              <div className="grid gap-2 md:grid-cols-2">
                {columnsQuery.data.data.map((column) => (
                  <Card key={`${listing.dataset.id}:${column.column_name}`} className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-sm">{column.column_name}</span>
                      <div className="flex items-center gap-1">
                        <Badge variant="outline">{column.data_type}</Badge>
                        {column.is_pii && <Badge variant="outline">PII</Badge>}
                      </div>
                    </div>
                    <p className="text-sm text-[var(--muted-foreground)]">
                      {column.description ?? '설명 없음'}
                    </p>
                  </Card>
                ))}
              </div>
            ) : (
              <EmptyState title="컬럼 정보가 없습니다." />
            )}
          </Card>

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Lineage</h2>
            {lineageQuery.isPending ? (
              <div className="h-48 animate-pulse rounded bg-[var(--muted)]" />
            ) : lineageQuery.isError ? (
              <ErrorCard
                message={(lineageQuery.error as Error).message}
                onRetry={lineageQuery.refetch}
              />
            ) : lineageQuery.data ? (
              <LineageViewer
                datasetId={listing.dataset.id}
                graph={lineageQuery.data.data}
                isSaving={false}
                onSave={async () => {}}
                onNavigateDataset={handleNavigateDataset}
              />
            ) : (
              <EmptyState title="Lineage 정보가 없습니다." />
            )}
          </Card>

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Business needs</h2>
            <ListingBusinessNeeds needs={listing.business_needs} />
          </Card>

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Resources</h2>
            <ListingResourceList resources={listing.resources} />
          </Card>

          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Related listings</h2>
            {listing.related_listings.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2">
                {listing.related_listings.map((related) => (
                  <ListingCard key={related.id} listing={related} />
                ))}
              </div>
            ) : (
              <EmptyState title="연관 listing이 없습니다." />
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <ListingOwnerPanel owner={listing.owner} />
          <Card className="space-y-3">
            <h2 className="text-lg font-semibold">Dataset identity</h2>
            <div className="space-y-2 text-sm text-[var(--muted-foreground)]">
              <p>ID: {listing.dataset.id}</p>
              <p>Slug: {listing.dataset.slug}</p>
              <p>Updated at: {new Date(listing.dataset.updated_at).toLocaleString('ko-KR')}</p>
              <p>Preview available: {listing.dataset.preview_available ? 'Yes' : 'No'}</p>
            </div>
          </Card>
        </div>
      </div>
    </section>
  )
}
