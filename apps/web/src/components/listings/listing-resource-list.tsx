import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { ListingResource } from '@pseudolab/shared-types'
import { useState } from 'react'

function resourceTypeLabel(type: ListingResource['type']): string {
  switch (type) {
    case 'sql':
      return 'SQL'
    case 'api':
      return 'API'
    case 'notebook':
      return 'Notebook'
    case 'documentation':
      return 'Documentation'
    default:
      return type
  }
}

export function ListingResourceList({ resources }: { resources: ListingResource[] }) {
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const handleCopy = async (resource: ListingResource) => {
    if (!resource.content || typeof navigator === 'undefined' || !navigator.clipboard) {
      return
    }

    await navigator.clipboard.writeText(resource.content)
    setCopiedId(resource.id)
    window.setTimeout(
      () => setCopiedId((current) => (current === resource.id ? null : current)),
      1200,
    )
  }

  if (resources.length === 0) {
    return <p className="text-sm text-[var(--muted-foreground)]">등록된 quick start가 없습니다.</p>
  }

  return (
    <div className="space-y-3">
      {resources.map((resource) => (
        <Card key={resource.id} className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium">{resource.title}</h3>
                <Badge variant="outline">{resourceTypeLabel(resource.type)}</Badge>
              </div>
              {resource.summary && (
                <p className="text-sm text-[var(--muted-foreground)]">{resource.summary}</p>
              )}
            </div>
            <div className="flex gap-2">
              {resource.url && (
                <a href={resource.url}>
                  <Button type="button" variant="outline" size="sm">
                    열기
                  </Button>
                </a>
              )}
              {resource.content && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void handleCopy(resource)}
                >
                  {copiedId === resource.id ? '복사됨' : '복사'}
                </Button>
              )}
            </div>
          </div>

          {resource.content && (
            <pre className="overflow-x-auto rounded-md bg-[var(--muted)] p-3 text-xs">
              <code>{resource.content}</code>
            </pre>
          )}

          {resource.related_dataset_ids.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {resource.related_dataset_ids.map((datasetId) => (
                <Badge key={`${resource.id}:${datasetId}`} variant="outline">
                  {datasetId}
                </Badge>
              ))}
            </div>
          )}
        </Card>
      ))}
    </div>
  )
}
