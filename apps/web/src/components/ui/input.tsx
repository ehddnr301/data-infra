import { cn } from '@/lib/utils'
import type { InputHTMLAttributes } from 'react'

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'h-9 w-full rounded-md border border-[var(--border)] bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-black/20',
        className,
      )}
      {...props}
    />
  )
}
