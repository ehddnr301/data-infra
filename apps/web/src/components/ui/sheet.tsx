import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

type SheetProps = HTMLAttributes<HTMLDivElement> & {
  open: boolean
}

export function Sheet({ className, open, ...props }: SheetProps) {
  if (!open) {
    return null
  }

  return (
    <div
      className={cn('fixed inset-0 z-40 bg-black/20 md:hidden', className)}
      role="dialog"
      aria-modal="true"
      {...props}
    />
  )
}
