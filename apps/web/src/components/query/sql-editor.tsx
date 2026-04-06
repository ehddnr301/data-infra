import { SQLite, sql } from '@codemirror/lang-sql'
import { EditorState } from '@codemirror/state'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView, placeholder as cmPlaceholder, keymap } from '@codemirror/view'
import { basicSetup } from 'codemirror'
import { useCallback, useEffect, useRef } from 'react'

type SqlEditorProps = {
  value: string
  onChange: (value: string) => void
  onExecute: () => void
  schema?: Record<string, string[]>
}

export function SqlEditor({ value, onChange, onExecute, schema }: SqlEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const onChangeRef = useRef(onChange)
  const onExecuteRef = useRef(onExecute)

  onChangeRef.current = onChange
  onExecuteRef.current = onExecute

  // biome-ignore lint/correctness/useExhaustiveDependencies: value is only used as initial doc; updates are handled by the separate useEffect below
  const createView = useCallback(() => {
    if (!containerRef.current) return

    if (viewRef.current) {
      viewRef.current.destroy()
    }

    const executeKeymap = keymap.of([
      {
        key: 'Ctrl-Enter',
        run: () => {
          onExecuteRef.current()
          return true
        },
      },
      {
        key: 'Mod-Enter',
        run: () => {
          onExecuteRef.current()
          return true
        },
      },
    ])

    const updateListener = EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        onChangeRef.current(update.state.doc.toString())
      }
    })

    const state = EditorState.create({
      doc: value,
      extensions: [
        basicSetup,
        sql({ dialect: SQLite, schema, upperCaseKeywords: true }),
        oneDark,
        executeKeymap,
        updateListener,
        cmPlaceholder('SELECT * FROM table_name LIMIT 10'),
        EditorView.theme({
          '&': { fontSize: '14px' },
          '.cm-editor': { borderRadius: '0.5rem' },
          '.cm-scroller': { minHeight: '160px', maxHeight: '320px', overflow: 'auto' },
        }),
      ],
    })

    viewRef.current = new EditorView({
      state,
      parent: containerRef.current,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schema])

  useEffect(() => {
    createView()
    return () => {
      viewRef.current?.destroy()
      viewRef.current = null
    }
  }, [createView])

  useEffect(() => {
    const view = viewRef.current
    if (view && view.state.doc.toString() !== value) {
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: value },
      })
    }
  }, [value])

  return (
    <div ref={containerRef} className="overflow-hidden rounded-lg border border-[var(--border)]" />
  )
}
