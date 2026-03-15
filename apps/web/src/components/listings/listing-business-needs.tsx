import { Card } from '@/components/ui/card'
import type { ListingBusinessNeed } from '@pseudolab/shared-types'

export function ListingBusinessNeeds({ needs }: { needs: ListingBusinessNeed[] }) {
  if (needs.length === 0) {
    return (
      <p className="text-sm text-[var(--muted-foreground)]">등록된 business need가 없습니다.</p>
    )
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {needs.map((need) => (
        <Card key={need.id} className="space-y-2">
          <p className="text-sm font-semibold">{need.title}</p>
          <p className="text-sm text-[var(--muted-foreground)]">{need.summary}</p>
        </Card>
      ))}
    </div>
  )
}
