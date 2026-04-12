import { apiPost } from '@/lib/api-client'
import { useAuth } from '@/lib/auth-context'
import { useNavigate } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'

type ExchangeResponse = {
  success: boolean
  data: { token: string; email: string; name: string; role: string }
}

export function AuthCallbackPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const processed = useRef(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (processed.current) return
    processed.current = true

    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')

    // Strip code from URL immediately
    window.history.replaceState({}, '', '/auth/callback')

    if (!code) {
      navigate({ to: '/' })
      return
    }

    // Exchange one-time code for JWT
    apiPost<ExchangeResponse>('/auth/exchange', { code })
      .then((res) => {
        login(res.data.token, res.data.email, res.data.name, res.data.role)
        navigate({ to: '/' })
      })
      .catch(() => {
        setError('로그인 처리에 실패했습니다. 다시 시도해주세요.')
      })
  }, [login, navigate])

  if (error) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center py-16">
      <p className="text-sm text-[var(--muted-foreground)]">로그인 처리 중...</p>
    </div>
  )
}
