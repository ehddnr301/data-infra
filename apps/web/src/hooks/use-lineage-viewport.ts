import type { LineageViewport } from '@pseudolab/shared-types'

const DEFAULT_VIEWPORT: LineageViewport = {
  x: 0,
  y: 0,
  zoom: 1,
}

function getViewportKey(datasetId: string): string {
  return `lineage-viewport-${datasetId}`
}

function isValidViewport(input: unknown): input is LineageViewport {
  if (typeof input !== 'object' || input === null || Array.isArray(input)) {
    return false
  }

  const value = input as Record<string, unknown>
  return (
    typeof value.x === 'number' && typeof value.y === 'number' && typeof value.zoom === 'number'
  )
}

export function readLineageViewport(datasetId: string): LineageViewport {
  if (!datasetId) {
    return DEFAULT_VIEWPORT
  }

  try {
    const raw = window.localStorage.getItem(getViewportKey(datasetId))
    if (!raw) {
      return DEFAULT_VIEWPORT
    }

    const parsed = JSON.parse(raw)
    if (!isValidViewport(parsed)) {
      return DEFAULT_VIEWPORT
    }

    return parsed
  } catch {
    return DEFAULT_VIEWPORT
  }
}

export function writeLineageViewport(datasetId: string, viewport: LineageViewport): void {
  if (!datasetId) {
    return
  }

  try {
    window.localStorage.setItem(getViewportKey(datasetId), JSON.stringify(viewport))
  } catch {
    return
  }
}

export function useLineageViewport(datasetId: string) {
  return {
    viewport: readLineageViewport(datasetId),
    saveViewport: (viewport: LineageViewport) => writeLineageViewport(datasetId, viewport),
  }
}

export { DEFAULT_VIEWPORT }
