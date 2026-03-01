import { EmptyState } from '@/components/empty-state'
import { ErrorCard } from '@/components/error-card'
import { TermForm } from '@/components/glossary/term-form'
import {
  useCreateGlossaryTerm,
  useDeleteGlossaryTerm,
  useGlossaryTerm,
  useGlossaryTerms,
  useUpdateGlossaryTerm,
} from '@/hooks/use-glossary'
import type { DomainName } from '@pseudolab/shared-types'
import { useNavigate, useParams } from '@tanstack/react-router'

export function GlossaryFormPage() {
  const navigate = useNavigate()
  const params = useParams({ strict: false })
  const termId = typeof params.termId === 'string' ? params.termId : undefined
  const isEdit = Boolean(termId)

  const detailQuery = useGlossaryTerm(termId ?? '')
  const allTermsQuery = useGlossaryTerms({ page: 1, pageSize: 200 })
  const createMutation = useCreateGlossaryTerm()
  const updateMutation = useUpdateGlossaryTerm()
  const deleteMutation = useDeleteGlossaryTerm()

  if (isEdit && detailQuery.isPending) {
    return (
      <section className="space-y-2">
        <div className="h-9 rounded bg-[var(--muted)] animate-pulse" />
        <div className="h-52 rounded bg-[var(--muted)] animate-pulse" />
      </section>
    )
  }

  if (isEdit && detailQuery.isError) {
    return <ErrorCard message="용어를 불러올 수 없습니다." onRetry={() => detailQuery.refetch()} />
  }

  if (isEdit && !detailQuery.data?.data) {
    return <EmptyState title="용어를 찾을 수 없습니다." />
  }

  const initial = detailQuery.data?.data

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">{isEdit ? '용어 수정' : '용어 생성'}</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          {isEdit ? '용어 정보를 수정합니다.' : '새 용어를 추가합니다.'}
        </p>
      </div>

      <TermForm
        mode={isEdit ? 'edit' : 'create'}
        initialValue={
          initial
            ? {
                domain: initial.domain,
                term: initial.term,
                definition: initial.definition,
                related_terms: initial.related_terms,
              }
            : {
                domain: 'github' as DomainName,
                term: '',
                definition: '',
                related_terms: [],
              }
        }
        allTerms={allTermsQuery.data?.data ?? []}
        excludeId={initial?.id}
        submitLabel={isEdit ? '수정 저장' : '용어 생성'}
        isSubmitting={createMutation.isPending || updateMutation.isPending}
        onCancel={() => {
          if (isEdit && termId) {
            void navigate({ to: '/glossary/$termId', params: { termId } })
            return
          }

          void navigate({ to: '/glossary' })
        }}
        onSubmit={async (value) => {
          if (isEdit && termId) {
            const result = await updateMutation.mutateAsync({
              id: termId,
              input: {
                term: value.term,
                definition: value.definition,
                related_terms: value.related_terms,
              },
            })
            void navigate({
              to: '/glossary/$termId',
              params: { termId: result.data.id },
            })
            return
          }

          const result = await createMutation.mutateAsync({
            domain: value.domain,
            term: value.term,
            definition: value.definition,
            related_terms: value.related_terms,
          })

          void navigate({
            to: '/glossary/$termId',
            params: { termId: result.data.id },
          })
        }}
        onDelete={
          isEdit && termId
            ? async () => {
                const confirmed = window.confirm('정말 삭제하시겠습니까?')
                if (!confirmed) {
                  return
                }

                await deleteMutation.mutateAsync(termId)
                void navigate({ to: '/glossary' })
              }
            : undefined
        }
        isDeleting={deleteMutation.isPending}
      />

      {(createMutation.error || updateMutation.error || deleteMutation.error) && (
        <ErrorCard
          message={
            (createMutation.error as Error)?.message ||
            (updateMutation.error as Error)?.message ||
            (deleteMutation.error as Error)?.message ||
            '요청 처리 중 오류가 발생했습니다.'
          }
        />
      )}
    </section>
  )
}
