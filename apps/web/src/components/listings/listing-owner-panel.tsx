import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import type { ListingOwner } from '@pseudolab/shared-types'

export function ListingOwnerPanel({ owner }: { owner: ListingOwner }) {
  return (
    <Card className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">Owner</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          {owner.display_name}
          {owner.team_name ? ` · ${owner.team_name}` : ''}
        </p>
      </div>

      {owner.role_title && <Badge variant="outline">{owner.role_title}</Badge>}
      {owner.bio && <p className="text-sm text-[var(--muted-foreground)]">{owner.bio}</p>}

      <div className="space-y-1 text-sm">
        {owner.contact_email && <p>Email: {owner.contact_email}</p>}
        {owner.slack_channel && <p>Slack: {owner.slack_channel}</p>}
      </div>
    </Card>
  )
}
