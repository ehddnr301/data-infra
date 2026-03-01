import { cn } from '@/lib/utils'
import { X } from 'lucide-react'
import { type DialogHTMLAttributes, type HTMLAttributes, useEffect } from 'react'

type SheetProps = HTMLAttributes<HTMLDivElement> & {
  open: boolean
  onOpenChange?: (open: boolean) => void
}

export function Sheet({ className, open, onOpenChange, children, ...props }: SheetProps) {
  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange?.(false)
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onOpenChange])

  if (!open) return null

  return (
    <div className={cn('fixed inset-0 z-40', className)} {...props}>
      <button
        type="button"
        className="absolute inset-0 bg-black/20"
        onClick={() => onOpenChange?.(false)}
        aria-label="닫기"
      />
      {children}
    </div>
  )
}

export function SheetContent({
  className,
  children,
  ...props
}: DialogHTMLAttributes<HTMLDialogElement>) {
  return (
    <dialog
      open
      className={cn(
        'fixed inset-y-0 right-0 z-50 w-full sm:w-96 bg-[var(--background)] border-l border-[var(--border)] shadow-lg',
        'animate-in slide-in-from-right duration-200',
        className,
      )}
      {...props}
    >
      <div className="flex flex-col h-full overflow-y-auto p-4">{children}</div>
    </dialog>
  )
}

export function SheetHeader({
  className,
  children,
  onClose,
  ...props
}: HTMLAttributes<HTMLDivElement> & { onClose?: () => void }) {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)} {...props}>
      <div>{children}</div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded hover:bg-[var(--muted)] text-[var(--muted-foreground)]"
          aria-label="닫기"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}

export function SheetTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('text-lg font-semibold', className)} {...props} />
}
