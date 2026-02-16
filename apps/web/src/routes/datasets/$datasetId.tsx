import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { useColumns, useDataset } from '@/hooks/use-catalog'
import { useParams } from '@tanstack/react-router'

export function DatasetDetailPage() {
  const { datasetId } = useParams({ from: '/datasets/$datasetId' })
  const datasetQuery = useDataset(datasetId)
  const columnsQuery = useColumns(datasetId)

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">데이터셋 상세</h1>
      <Card>
        {datasetQuery.isPending && (
          <p className="text-sm text-[var(--muted-foreground)]">불러오는 중...</p>
        )}
        {datasetQuery.isError && (
          <p className="text-sm text-red-600">데이터셋 정보를 불러올 수 없습니다.</p>
        )}

        {datasetQuery.data?.data && (
          <div className="space-y-2">
            <h2 className="text-lg font-semibold">{datasetQuery.data.data.name}</h2>
            <Badge>{datasetQuery.data.data.domain}</Badge>
            <p className="text-sm text-[var(--muted-foreground)]">
              {datasetQuery.data.data.description}
            </p>
            <Separator />
            <p className="text-sm">컬럼 수: {columnsQuery.data?.data.length ?? 0}</p>
          </div>
        )}
      </Card>
    </section>
  )
}
