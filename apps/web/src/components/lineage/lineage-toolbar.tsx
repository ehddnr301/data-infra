import { Button } from '@/components/ui/button'

type LineageToolbarProps = {
  isEditMode: boolean
  isSaving: boolean
  onToggleEdit: () => void
  onSave: () => void
  onCancel: () => void
  onFitView: () => void
}

export function LineageToolbar({
  isEditMode,
  isSaving,
  onToggleEdit,
  onSave,
  onCancel,
  onFitView,
}: LineageToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {!isEditMode ? (
        <Button variant="outline" size="sm" onClick={onToggleEdit}>
          Edit
        </Button>
      ) : (
        <>
          <Button size="sm" onClick={onSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
          <Button variant="outline" size="sm" onClick={onCancel} disabled={isSaving}>
            Cancel
          </Button>
        </>
      )}
      <Button variant="ghost" size="sm" onClick={onFitView}>
        FitView
      </Button>
    </div>
  )
}
