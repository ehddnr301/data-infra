import { AppFooter } from '@/components/layout/app-footer'
import { AppHeader } from '@/components/layout/app-header'
import { AppSidebar } from '@/components/layout/app-sidebar'
import { Sheet } from '@/components/ui/sheet'
import { SidebarInset } from '@/components/ui/sidebar'
import { Outlet } from '@tanstack/react-router'
import { useState } from 'react'

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader onOpenSidebar={() => setMobileOpen(true)} />
      <div className="mx-auto flex w-full max-w-6xl flex-1">
        <AppSidebar />
        <Sheet open={mobileOpen} onClick={() => setMobileOpen(false)}>
          <div
            className="h-full w-64 bg-white"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                setMobileOpen(false)
              }
            }}
            role="presentation"
          >
            <AppSidebar
              className="block w-full border-r-0"
              onNavigate={() => setMobileOpen(false)}
            />
          </div>
        </Sheet>
        <SidebarInset>
          <main className="p-4">
            <Outlet />
          </main>
          <AppFooter />
        </SidebarInset>
      </div>
    </div>
  )
}
