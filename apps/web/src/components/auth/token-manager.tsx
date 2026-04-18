import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { apiDelete, apiGet, apiPost } from '@/lib/api-client'
import { Check, Copy, Key, Plus, Trash2 } from 'lucide-react'
import { type FormEvent, useCallback, useEffect, useState } from 'react'

type ApiToken = {
  id: string
  name: string
  token_prefix: string
  created_at: string
  last_used_at: string | null
}

type TokenListResponse = { success: boolean; data: ApiToken[] }
type TokenCreateResponse = {
  success: boolean
  data: { id: string; name: string; token: string; token_prefix: string; created_at: string }
}

const LLMS_TXT_URL = 'https://master.pseudolab-web.pages.dev/llms.txt'

function buildClaudePrompt(token: string): string {
  return `당신은 PseudoLab 데이터 플랫폼의 데이터 분석 어시스턴트입니다.

## 인증 정보
API Token: ${token}
Base URL: https://pseudolab-api.dwlee-416.workers.dev

모든 API 요청에 아래 헤더를 포함하세요:
Authorization: Bearer ${token}

## 플랫폼 가이드
아래 URL에서 전체 API 사양과 테이블 적재 방식(incremental/snapshot) 주의사항을 확인하세요:
${LLMS_TXT_URL}

## 워크플로우

1. **데이터셋 파악**: GET /api/ai/manifest 로 전체 테이블 목록을 조회하세요.
2. **기존 인사이트 확인**: 분석 대상 데이터셋의 댓글을 GET /api/datasets/{dataset_id}/comments 로 먼저 확인하세요. 다른 사용자나 AI가 남긴 limitation, usage 팁, 주의사항이 있을 수 있습니다.
3. **SQL 분석**: 사용자의 질문에 맞는 SQL을 작성하여 POST /api/query 로 실행하세요.
4. **인사이트 공유**: 분석 결과를 설명할 때, 다른 사용자에게도 유용할 인사이트가 있다면 댓글 후보를 함께 제시하세요. 사용자가 다음 메시지에서 거부하지 않으면 POST /api/datasets/{dataset_id}/comments 로 작성하세요.

## 댓글 작성 기준

댓글은 개인적 분석 결과가 아니라 **다른 사용자에게도 재사용 가능한 지식**일 때만 남기세요:
- \`limitation\` — 데이터 한계/주의사항 (예: "2024년 이전 데이터 없음", "base_date 필터 필수")
- \`purpose\` — 이 데이터셋의 활용 목적 (예: "기여자 활동 분석에 적합")
- \`usage\` — 유용한 쿼리 패턴이나 사용 팁 (예: "org='pseudolab' 필터 필수")

댓글 작성 시 source는 반드시 "ai-assisted"로 설정하세요.

### 댓글 제안 방식 (opt-out)
분석 결과를 설명한 뒤, 재사용 가능한 인사이트를 발견하면 **같은 응답 안에서** 댓글 후보를 아래 형식으로 제시하세요:

> **남길 댓글:**
> - [category] 댓글 내용

사용자가 다음 메시지에서 "남기지 마", "댓글 불필요" 등으로 거부하면 작성하지 마세요. 별다른 거부 없이 대화가 이어지면 해당 댓글을 작성하고 "댓글을 남겼습니다"라고 알려주세요.

## 주의사항
- SELECT만 가능하며 LIMIT 최대 100입니다.
- snapshot 테이블은 base_date 필터 없이 집계하면 중복 카운트됩니다. 반드시 llms.txt의 적재 방식 안내를 확인하세요.`
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Button variant="outline" size="sm" onClick={handleCopy} className="gap-1">
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      {copied ? '복사됨' : label}
    </Button>
  )
}

export function TokenManager() {
  const [tokens, setTokens] = useState<ApiToken[]>([])
  const [newTokenName, setNewTokenName] = useState('')
  const [newDisplayName, setNewDisplayName] = useState('')
  const [createdToken, setCreatedToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchTokens = useCallback(async () => {
    try {
      const res = await apiGet<TokenListResponse>('/auth/tokens')
      setTokens(res.data)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchTokens()
  }, [fetchTokens])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    const name = newTokenName.trim()
    if (!name) return
    setLoading(true)
    try {
      const displayName = newDisplayName.trim() || undefined
      const res = await apiPost<TokenCreateResponse>('/auth/tokens', {
        name,
        display_name: displayName,
      })
      setCreatedToken(res.data.token)
      setNewTokenName('')
      setNewDisplayName('')
      fetchTokens()
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  async function handleRevoke(id: string) {
    await apiDelete(`/auth/tokens/${id}`)
    fetchTokens()
  }

  return (
    <Card className="space-y-4 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Key className="h-4 w-4" />내 API 토큰
      </div>

      {/* Token created — show token + Claude prompt */}
      {createdToken && (
        <div className="space-y-3 rounded-md border border-green-300 bg-green-50 p-3 text-sm">
          <div>
            <p className="mb-2 font-medium text-green-800">
              토큰이 생성되었습니다. 이 값은 다시 확인할 수 없으니 반드시 복사하세요.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 break-all rounded bg-white px-2 py-1 text-xs">
                {createdToken}
              </code>
              <CopyButton text={createdToken} label="토큰 복사" />
            </div>
          </div>

          <div className="border-t border-green-200 pt-3">
            <p className="mb-2 font-medium text-green-800">
              Claude에 아래 프롬프트를 붙여넣으면 바로 데이터 분석을 시작할 수 있습니다.
            </p>
            <div className="max-h-32 overflow-y-auto rounded bg-white p-2 text-xs text-gray-700">
              <pre className="whitespace-pre-wrap">{buildClaudePrompt(createdToken)}</pre>
            </div>
            <div className="mt-2 flex gap-2">
              <CopyButton text={buildClaudePrompt(createdToken)} label="프롬프트 복사" />
            </div>
          </div>

          <Button variant="ghost" size="sm" onClick={() => setCreatedToken(null)}>
            닫기
          </Button>
        </div>
      )}

      {/* Create form */}
      <form onSubmit={handleCreate} className="space-y-2">
        <div className="flex gap-2">
          <Input
            placeholder="토큰 이름 (예: 내 봇)"
            value={newTokenName}
            onChange={(e) => setNewTokenName(e.target.value)}
            className="flex-1"
          />
          <Button type="submit" disabled={loading || !newTokenName.trim()} size="sm">
            <Plus className="mr-1 h-3 w-3" />
            발급
          </Button>
        </div>
        <Input
          placeholder="표시 이름 / 별칭 (선택 — 댓글에 실명 대신 표시)"
          value={newDisplayName}
          onChange={(e) => setNewDisplayName(e.target.value)}
        />
      </form>

      {/* Token list */}
      {tokens.length > 0 && (
        <div className="space-y-2">
          {tokens.map((t) => (
            <div
              key={t.id}
              className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
            >
              <div className="space-y-0.5">
                <div className="font-medium">{t.name}</div>
                <div className="text-xs text-[var(--muted-foreground)]">
                  <code>{t.token_prefix}...</code>
                  {' · '}
                  {new Date(t.created_at).toLocaleDateString('ko-KR')}
                  {t.last_used_at &&
                    ` · 마지막 사용: ${new Date(t.last_used_at).toLocaleDateString('ko-KR')}`}
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => handleRevoke(t.id)}>
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {tokens.length === 0 && !createdToken && (
        <p className="text-xs text-[var(--muted-foreground)]">
          발급된 토큰이 없습니다. 봇이나 스크립트에서 API를 호출하려면 토큰을 발급하세요.
        </p>
      )}
    </Card>
  )
}
