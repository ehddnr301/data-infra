import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { AlertCircle } from 'lucide-react'

export function ErrorCard({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Card className="border-red-300">
      <div className="flex items-center gap-2">
        <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
        <p className="text-sm text-red-600">{message}</p>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            다시 시도
          </Button>
        )}
      </div>
    </Card>
  )
}
