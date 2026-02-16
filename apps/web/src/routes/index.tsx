import { Card } from '@/components/ui/card'

export function HomePage() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <h2 className="text-sm text-[var(--muted-foreground)]">도메인</h2>
        <p className="mt-2 text-2xl font-semibold">4</p>
      </Card>
      <Card>
        <h2 className="text-sm text-[var(--muted-foreground)]">데이터셋</h2>
        <p className="mt-2 text-2xl font-semibold">0</p>
      </Card>
      <Card>
        <h2 className="text-sm text-[var(--muted-foreground)]">상태</h2>
        <p className="mt-2 text-2xl font-semibold">Bootstrapped</p>
      </Card>
    </div>
  )
}
