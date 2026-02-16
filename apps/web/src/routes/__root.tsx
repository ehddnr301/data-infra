import { AppLayout } from '@/components/layout/app-layout'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'

export function RootRouteComponent() {
  return (
    <>
      <AppLayout />
      <TanStackRouterDevtools position="bottom-right" />
    </>
  )
}

export function RootErrorComponent() {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      페이지를 불러오는 중 오류가 발생했습니다.
    </div>
  )
}

export function RootNotFoundComponent() {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-white p-6">
      <h2 className="text-lg font-semibold">404</h2>
      <p className="text-sm text-[var(--muted-foreground)]">요청한 페이지를 찾을 수 없습니다.</p>
    </div>
  )
}
