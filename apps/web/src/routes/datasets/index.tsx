import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table'
import { useDatasets } from '@/hooks/use-catalog'
import { Link } from '@tanstack/react-router'

export function DatasetsPage() {
  const { data, isPending, isError, error } = useDatasets({ page: 1, pageSize: 20 })

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">데이터셋</h1>
        <div className="w-60">
          <Input placeholder="검색 (준비 중)" disabled />
        </div>
      </div>

      <Card>
        {isPending && <p className="text-sm text-[var(--muted-foreground)]">불러오는 중...</p>}
        {isError && (
          <p className="text-sm text-red-600">
            {(error as Error).message || '데이터셋 조회 중 오류가 발생했습니다.'}
          </p>
        )}

        {!isPending && !isError && (
          <Table>
            <THead>
              <TR>
                <TH>이름</TH>
                <TH>도메인</TH>
                <TH>설명</TH>
              </TR>
            </THead>
            <TBody>
              {data?.data.length ? (
                data.data.map((dataset) => (
                  <TR key={dataset.id}>
                    <TD>
                      <Link to="/datasets/$datasetId" params={{ datasetId: dataset.id }}>
                        {dataset.name}
                      </Link>
                    </TD>
                    <TD>
                      <Badge>{dataset.domain}</Badge>
                    </TD>
                    <TD>{dataset.description}</TD>
                  </TR>
                ))
              ) : (
                <TR>
                  <TD className="text-[var(--muted-foreground)]" colSpan={3}>
                    데이터셋이 없습니다.
                  </TD>
                </TR>
              )}
            </TBody>
          </Table>
        )}
      </Card>
    </section>
  )
}
