export function DatasetListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-12 bg-[var(--muted)] animate-pulse rounded" />
      ))}
    </div>
  )
}

export function DatasetDetailSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-48 bg-[var(--muted)] animate-pulse rounded" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 bg-[var(--muted)] animate-pulse rounded" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 bg-[var(--muted)] animate-pulse rounded" />
        ))}
      </div>
    </div>
  )
}
