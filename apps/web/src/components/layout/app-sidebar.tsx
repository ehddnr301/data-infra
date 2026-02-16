import { Sidebar } from '@/components/ui/sidebar'
import { Link } from '@tanstack/react-router'
import { BookOpen, Database, Info, LayoutDashboard } from 'lucide-react'

type AppSidebarProps = {
  className?: string
  onNavigate?: () => void
}

export function AppSidebar({ className, onNavigate }: AppSidebarProps) {
  return (
    <Sidebar className={className}>
      <nav className="flex flex-col gap-1 p-3">
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-black/5"
          onClick={onNavigate}
        >
          <LayoutDashboard className="h-4 w-4" />
          대시보드
        </Link>
        <Link
          to="/datasets"
          className="inline-flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-black/5"
          onClick={onNavigate}
        >
          <Database className="h-4 w-4" />
          데이터셋
        </Link>
        <Link
          to="/glossary"
          className="inline-flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-black/5"
          onClick={onNavigate}
        >
          <BookOpen className="h-4 w-4" />
          용어집
        </Link>
        <Link
          to="/about"
          className="inline-flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-black/5"
          onClick={onNavigate}
        >
          <Info className="h-4 w-4" />
          소개
        </Link>
      </nav>
    </Sidebar>
  )
}
