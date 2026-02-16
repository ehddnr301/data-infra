import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

export function NavigationMenu({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <nav className={cn('flex items-center gap-2', className)} {...props} />
}
