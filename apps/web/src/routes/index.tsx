import { Card } from '@/components/ui/card'
import { Link } from '@tanstack/react-router'
import { Github, MessageSquare, Store } from 'lucide-react'

export function HomePage() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <h2 className="text-sm text-[var(--muted-foreground)]">Canonical surface</h2>
          <p className="mt-2 text-2xl font-semibold">Dataset Marketplace</p>
        </Card>
        <Card>
          <h2 className="text-sm text-[var(--muted-foreground)]">Domain hubs</h2>
          <p className="mt-2 text-2xl font-semibold">GitHub · Discord</p>
        </Card>
        <Card>
          <h2 className="text-sm text-[var(--muted-foreground)]">Legacy datasets routes</h2>
          <p className="mt-2 text-2xl font-semibold">Removed</p>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Link to="/listings" className="block">
          <Card className="space-y-2 transition-colors hover:border-[var(--primary)]">
            <div className="flex items-center gap-2">
              <Store className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Browse listings</h2>
            </div>
            <p className="text-sm text-[var(--muted-foreground)]">
              모든 dataset product를 하나의 marketplace index에서 탐색합니다.
            </p>
          </Card>
        </Link>

        <Link to="/domains/$domainKey" params={{ domainKey: 'github' }} className="block">
          <Card className="space-y-2 transition-colors hover:border-[var(--primary)]">
            <div className="flex items-center gap-2">
              <Github className="h-5 w-5" />
              <h2 className="text-xl font-semibold">GitHub hub</h2>
            </div>
            <p className="text-sm text-[var(--muted-foreground)]">
              repository activity, releases, issues 관련 dataset product를 모아봅니다.
            </p>
          </Card>
        </Link>

        <Link to="/domains/$domainKey" params={{ domainKey: 'discord' }} className="block">
          <Card className="space-y-2 transition-colors hover:border-[var(--primary)]">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Discord hub</h2>
            </div>
            <p className="text-sm text-[var(--muted-foreground)]">
              community operations, moderation, collector health dataset product를 살펴봅니다.
            </p>
          </Card>
        </Link>
      </div>
    </div>
  )
}
