import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full bg-black/5 px-2 py-1 text-xs text-[var(--muted-foreground)]',
        className,
      )}
      {...props}
    />
  )
}
