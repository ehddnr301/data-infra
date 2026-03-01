export function DatasetListSkeleton() {
  return (
    <div className="space-y-2">
      {[
        'dataset-list-1',
        'dataset-list-2',
        'dataset-list-3',
        'dataset-list-4',
        'dataset-list-5',
      ].map((key) => (
        <div key={key} className="h-12 bg-[var(--muted)] animate-pulse rounded" />
      ))}
    </div>
  )
}

export function DatasetDetailSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-8 w-48 bg-[var(--muted)] animate-pulse rounded" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {['dataset-meta-1', 'dataset-meta-2', 'dataset-meta-3', 'dataset-meta-4'].map((key) => (
          <div key={key} className="h-16 bg-[var(--muted)] animate-pulse rounded" />
        ))}
      </div>
      <div className="space-y-2">
        {['dataset-row-1', 'dataset-row-2', 'dataset-row-3', 'dataset-row-4'].map((key) => (
          <div key={key} className="h-10 bg-[var(--muted)] animate-pulse rounded" />
        ))}
      </div>
    </div>
  )
}
