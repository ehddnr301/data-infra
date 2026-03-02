import {
  prettyLineageEdgeLabel,
  truncateLineageEdgeLabel,
} from '@/components/lineage/lineage-edge-label'
import { expect, it } from 'vitest'

it('extracts bracket action and keeps JSONL context', () => {
  expect(prettyLineageEdgeLabel('Discord REST API → [fetch] → 로컬 JSONL')).toBe('fetch JSONL')
})

it('falls back to compact original label', () => {
  expect(prettyLineageEdgeLabel('transform-load')).toBe('transform-load')
})

it('truncates long labels with ellipsis', () => {
  expect(truncateLineageEdgeLabel('long-label-value', 8)).toBe('long-la…')
})
