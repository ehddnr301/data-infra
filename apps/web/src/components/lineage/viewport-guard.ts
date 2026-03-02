import type { LineageNode, LineageViewport } from '@pseudolab/shared-types'

const ASSUMED_NODE_WIDTH = 180
const ASSUMED_NODE_HEIGHT = 64
const VIEWPORT_MARGIN = 160

function isNodeVisible(
  node: LineageNode,
  viewport: LineageViewport,
  containerWidth: number,
  containerHeight: number,
): boolean {
  const zoom = viewport.zoom
  const left = node.position.x * zoom + viewport.x
  const top = node.position.y * zoom + viewport.y
  const width = ASSUMED_NODE_WIDTH * zoom
  const height = ASSUMED_NODE_HEIGHT * zoom

  const right = left + width
  const bottom = top + height

  return (
    right >= -VIEWPORT_MARGIN &&
    left <= containerWidth + VIEWPORT_MARGIN &&
    bottom >= -VIEWPORT_MARGIN &&
    top <= containerHeight + VIEWPORT_MARGIN
  )
}

export function shouldRestorePersistedViewport(
  nodes: LineageNode[],
  viewport: LineageViewport,
  containerWidth: number,
  containerHeight: number,
): boolean {
  if (nodes.length === 0) {
    return false
  }

  if (containerWidth <= 0 || containerHeight <= 0) {
    return false
  }

  return nodes.some((node) => isNodeVisible(node, viewport, containerWidth, containerHeight))
}
