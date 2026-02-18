import { cn } from '@/lib/utils'
import { type VariantProps, cva } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2 py-1 text-xs',
  {
    variants: {
      variant: {
        default: 'bg-black/5 text-[var(--muted-foreground)]',
        secondary: 'bg-[var(--muted)] text-[var(--muted-foreground)]',
        outline: 'border border-[var(--border)] text-[var(--foreground)]',
        destructive: 'bg-red-100 text-red-700',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

type BadgeProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}
