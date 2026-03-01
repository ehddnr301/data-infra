import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { NavigationMenu } from '@/components/ui/navigation-menu'
import { useRecentSearches } from '@/hooks/use-recent-searches'
import { Link } from '@tanstack/react-router'
import { Database, Info, LayoutDashboard, Menu, Search } from 'lucide-react'
import { useState } from 'react'

type AppHeaderProps = {
  onOpenSidebar: () => void
}

export function AppHeader({ onOpenSidebar }: AppHeaderProps) {
  const [query, setQuery] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const { recentSearches, addRecentSearch } = useRecentSearches()

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
        <div className="relative hidden min-w-64 flex-1 max-w-sm md:block">
          <form
            action="/search"
            method="get"
            className="flex items-center gap-2"
            aria-label="글로벌 검색"
            onSubmit={() => {
              addRecentSearch(query)
            }}
          >
            <input type="hidden" name="type" value="all" />
            <Input
              type="search"
              name="q"
              value={query}
              onFocus={() => setIsFocused(true)}
              onBlur={() => {
                window.setTimeout(() => setIsFocused(false), 100)
              }}
              onChange={(event) => setQuery((event.target as HTMLInputElement).value)}
              placeholder="통합 검색"
              aria-label="통합 검색 입력"
              className="h-8"
            />
            <Button type="submit" size="sm" variant="outline" className="h-8 px-2">
              <Search className="h-4 w-4" />
            </Button>
          </form>
          {isFocused && recentSearches.length > 0 ? (
            <div className="absolute left-0 right-0 top-10 rounded-md border bg-white p-2 shadow-sm">
              <p className="mb-1 text-xs text-[var(--muted-foreground)]">최근 검색어</p>
              <div className="space-y-1">
                {recentSearches.slice(0, 5).map((item) => (
                  <a
                    key={item}
                    href={`/search?q=${encodeURIComponent(item)}&type=all`}
                    className="block rounded px-2 py-1 text-sm hover:bg-[var(--muted)]"
                    onMouseDown={() => addRecentSearch(item)}
                  >
                    {item}
                  </a>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  )
}
