import { GoogleLoginButton } from '@/components/auth/google-login-button'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/lib/auth-context'
import { KeyRound } from 'lucide-react'
import { type FormEvent, useState } from 'react'

export function LoginPage() {
  return (
    <div className="flex items-center justify-center py-16">
      <Card className="w-full max-w-md space-y-4 p-6">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <KeyRound className="h-5 w-5" />
          로그인
        </div>
        <p className="text-sm text-[var(--muted-foreground)]">
          SQL 쿼리 대시보드와 댓글 기능을 사용하려면 로그인이 필요합니다.
        </p>
        <GoogleLoginButton />
        {import.meta.env.DEV && (
          <>
            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-[var(--border)]" />
              <span className="text-xs text-[var(--muted-foreground)]">또는 (개발용)</span>
              <div className="h-px flex-1 bg-[var(--border)]" />
            </div>
            <InlineDevLogin />
          </>
        )}
      </Card>
    </div>
  )
}

function InlineDevLogin() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [token, setToken] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (email.trim() && token.trim()) {
      login(token.trim(), email.trim(), name.trim())
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="space-y-1">
        <label htmlFor="dev-email" className="text-sm font-medium">
          이메일 *
        </label>
        <Input
          id="dev-email"
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="dev-name" className="text-sm font-medium">
          이름
        </label>
        <Input
          id="dev-name"
          type="text"
          placeholder="홍길동"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="dev-token" className="text-sm font-medium">
          API 토큰 *
        </label>
        <Input
          id="dev-token"
          type="password"
          placeholder="Bearer token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          required
        />
      </div>
      <Button type="submit" variant="outline" className="w-full">
        개발용 로그인
      </Button>
    </form>
  )
}
