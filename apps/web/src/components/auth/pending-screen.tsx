import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { apiGet } from '@/lib/api-client'
import { useAuth } from '@/lib/auth-context'
import { Clock, LogOut, RefreshCw } from 'lucide-react'
import { useCallback, useState } from 'react'

type MeResponse = {
  success: boolean
  data: { email: string; name: string; role: string; picture: string | null }
}

export function PendingScreen() {
  const { auth, login, logout } = useAuth()
  const [checking, setChecking] = useState(false)

  const handleCheckStatus = useCallback(async () => {
    setChecking(true)
    try {
      const res = await apiGet<MeResponse>('/auth/me')
      if (res.data.role !== 'pending' && auth) {
        login(auth.token, auth.email, auth.name, res.data.role)
      }
    } catch {
      // ignore — still pending or token expired
    } finally {
      setChecking(false)
    }
  }, [auth, login])

  return (
    <div className="flex items-center justify-center py-16">
      <Card className="w-full max-w-md space-y-4 p-6 text-center">
        <Clock className="mx-auto h-12 w-12 text-[var(--muted-foreground)]" />
        <h2 className="text-lg font-semibold">승인 대기 중</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          관리자의 승인을 기다리고 있습니다.
          <br />
          승인 후 모든 기능을 사용할 수 있습니다.
        </p>
        {auth && <p className="text-xs text-[var(--muted-foreground)]">{auth.email}</p>}
        <div className="flex gap-2">
          <Button
            onClick={handleCheckStatus}
            disabled={checking}
            variant="outline"
            className="flex-1 gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${checking ? 'animate-spin' : ''}`} />
            상태 확인
          </Button>
          <Button onClick={logout} variant="ghost" className="flex-1 gap-2">
            <LogOut className="h-4 w-4" />
            로그아웃
          </Button>
        </div>
      </Card>
    </div>
  )
}
