import { cn } from '@/lib/utils'
import type { HTMLAttributes } from 'react'

export function Separator({ className, ...props }: HTMLAttributes<HTMLHRElement>) {
  return <hr className={cn('border-0 border-t border-[var(--border)]', className)} {...props} />
}
