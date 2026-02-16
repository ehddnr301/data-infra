import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

export function DropdownMenu({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('rounded-md border border-[var(--border)] bg-white p-2 shadow-sm', className)}
      {...props}
    />
  )
}
