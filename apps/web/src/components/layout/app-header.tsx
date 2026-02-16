import { Button } from '@/components/ui/button'
import { NavigationMenu } from '@/components/ui/navigation-menu'
import { Link } from '@tanstack/react-router'
import { Database, Info, LayoutDashboard, Menu } from 'lucide-react'

type AppHeaderProps = {
  onOpenSidebar: () => void
}

export function AppHeader({ onOpenSidebar }: AppHeaderProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-[var(--border)] bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-2">
          <Button className="md:hidden" variant="ghost" size="sm" onClick={onOpenSidebar}>
            <Menu className="h-4 w-4" />
          </Button>
          <p className="font-semibold tracking-tight">PseudoLab Data Catalog</p>
        </div>
        <NavigationMenu className="hidden md:flex">
          <Link to="/" className="inline-flex items-center gap-1 px-2 py-1 text-sm">
            <LayoutDashboard className="h-4 w-4" />
            대시보드
          </Link>
          <Link to="/datasets" className="inline-flex items-center gap-1 px-2 py-1 text-sm">
            <Database className="h-4 w-4" />
            데이터셋
          </Link>
          <Link to="/about" className="inline-flex items-center gap-1 px-2 py-1 text-sm">
            <Info className="h-4 w-4" />
            소개
          </Link>
        </NavigationMenu>
      </div>
    </header>
  )
}
