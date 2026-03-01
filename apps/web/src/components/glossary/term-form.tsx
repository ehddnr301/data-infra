import { RelatedTermsSelector } from '@/components/glossary/related-terms'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { DomainName, GlossaryTerm } from '@pseudolab/shared-types'
import { useEffect, useMemo, useState } from 'react'

type FormValue = {
  domain: DomainName
  term: string
  definition: string
  related_terms: string[]
}

type TermFormProps = {
  mode: 'create' | 'edit'
  initialValue?: FormValue
  allTerms: GlossaryTerm[]
  excludeId?: string
  submitLabel: string
  isSubmitting: boolean
  onSubmit: (value: FormValue) => void | Promise<void>
  onCancel: () => void
  onDelete?: () => void
  isDeleting?: boolean
}

const DOMAIN_OPTIONS: DomainName[] = ['github', 'discord', 'linkedin', 'members']

const EMPTY_VALUE: FormValue = {
  domain: 'github',
  term: '',
  definition: '',
  related_terms: [],
}

export function TermForm({
  mode,
  initialValue,
  allTerms,
  excludeId,
  submitLabel,
  isSubmitting,
  onSubmit,
  onCancel,
  onDelete,
  isDeleting,
}: TermFormProps) {
  const [value, setValue] = useState<FormValue>(initialValue ?? EMPTY_VALUE)

  useEffect(() => {
    setValue(initialValue ?? EMPTY_VALUE)
  }, [initialValue])

  const selectableTerms = useMemo(() => {
    return allTerms.filter((item) => item.domain === value.domain)
  }, [allTerms, value.domain])

  return (
    <Card className="p-4 space-y-4">
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          void onSubmit(value)
        }}
      >
        <div className="space-y-1">
          <p className="text-sm font-medium">도메인</p>
          <select
            className="h-9 rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
            value={value.domain}
            disabled={mode === 'edit'}
            onChange={(event) => {
              const nextDomain = event.target.value as DomainName
              setValue((prev) => ({
                ...prev,
                domain: nextDomain,
                related_terms: prev.related_terms.filter((id) => {
                  const term = allTerms.find((item) => item.id === id)
                  return term ? term.domain === nextDomain : false
                }),
              }))
            }}
          >
            {DOMAIN_OPTIONS.map((domain) => (
              <option key={domain} value={domain}>
                {domain}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <p className="text-sm font-medium">용어</p>
          <Input
            maxLength={120}
            placeholder="예: actor"
            value={value.term}
            onChange={(event) => {
              setValue((prev) => ({
                ...prev,
                term: (event.target as HTMLInputElement).value,
              }))
            }}
          />
        </div>

        <div className="space-y-1">
          <p className="text-sm font-medium">정의</p>
          <textarea
            className="min-h-28 w-full rounded-md border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
            placeholder="용어 정의를 입력하세요"
            value={value.definition}
            onChange={(event) => {
              setValue((prev) => ({
                ...prev,
                definition: event.target.value,
              }))
            }}
          />
        </div>

        <div className="space-y-1">
          <p className="text-sm font-medium">관련 용어</p>
          <RelatedTermsSelector
            terms={selectableTerms}
            selectedIds={value.related_terms}
            excludeId={excludeId}
            onChange={(nextIds) => {
              setValue((prev) => ({
                ...prev,
                related_terms: nextIds,
              }))
            }}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" disabled={isSubmitting}>
            {submitLabel}
          </Button>
          <Button type="button" variant="outline" onClick={onCancel}>
            취소
          </Button>
          {mode === 'edit' && onDelete ? (
            <Button type="button" variant="outline" disabled={isDeleting} onClick={onDelete}>
              삭제
            </Button>
          ) : null}
        </div>
      </form>
    </Card>
  )
}
