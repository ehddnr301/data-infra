import { shouldRestorePersistedViewport } from '@/components/lineage/viewport-guard'
import type { LineageNode, LineageViewport } from '@pseudolab/shared-types'
import { expect, it } from 'vitest'

function makeNode(x: number, y: number): LineageNode {
  return {
    id: `node-${x}-${y}`,
    type: 'dataset',
    position: { x, y },
    data: { datasetId: `node-${x}-${y}` },
  }
}

it('allows restore when at least one node is visible', () => {
  const viewport: LineageViewport = { x: 0, y: 0, zoom: 1 }
  const nodes = [makeNode(0, 0), makeNode(500, 0)]

  expect(shouldRestorePersistedViewport(nodes, viewport, 1200, 700)).toBe(true)
})

it('blocks restore when all nodes are off-screen', () => {
  const viewport: LineageViewport = { x: -10000, y: -10000, zoom: 1 }
  const nodes = [makeNode(0, 0), makeNode(500, 0)]

  expect(shouldRestorePersistedViewport(nodes, viewport, 1200, 700)).toBe(false)
})

it('blocks restore when container size is invalid', () => {
  const viewport: LineageViewport = { x: 0, y: 0, zoom: 1 }
  const nodes = [makeNode(0, 0)]

  expect(shouldRestorePersistedViewport(nodes, viewport, 0, 700)).toBe(false)
  expect(shouldRestorePersistedViewport(nodes, viewport, 1200, 0)).toBe(false)
})
