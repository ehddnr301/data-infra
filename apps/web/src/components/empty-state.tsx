import { Database } from 'lucide-react'

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center py-8 text-center">
      <Database className="h-10 w-10 text-[var(--muted-foreground)] mb-2" />
      <p className="font-medium">{title}</p>
      {description && <p className="text-sm text-[var(--muted-foreground)]">{description}</p>}
    </div>
  )
}
