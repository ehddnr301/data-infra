import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

export function Sidebar({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <aside
      className={cn('hidden w-64 border-r border-[var(--border)] bg-white md:block', className)}
      {...props}
    />
  )
}

export function SidebarInset({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('min-w-0 flex-1', className)} {...props} />
}
