import {
  DEFAULT_VIEWPORT,
  readLineageViewport,
  writeLineageViewport,
} from '@/hooks/use-lineage-viewport'
import { beforeEach, expect, it } from 'vitest'

beforeEach(() => {
  window.localStorage.clear()
})

it('reads default viewport when localStorage is empty', () => {
  expect(readLineageViewport('ds.github.repo.v1')).toEqual(DEFAULT_VIEWPORT)
})

it('writes and restores viewport from localStorage', () => {
  const viewport = { x: 42, y: -10, zoom: 1.25 }
  writeLineageViewport('ds.github.repo.v1', viewport)

  expect(readLineageViewport('ds.github.repo.v1')).toEqual(viewport)
})

it('returns default viewport for malformed localStorage JSON', () => {
  window.localStorage.setItem('lineage-viewport-ds.github.repo.v1', '{broken-json')

  expect(readLineageViewport('ds.github.repo.v1')).toEqual(DEFAULT_VIEWPORT)
})

it('returns default viewport for invalid zoom values', () => {
  window.localStorage.setItem(
    'lineage-viewport-ds.github.repo.v1',
    JSON.stringify({ x: 0, y: 0, zoom: 0 }),
  )

  expect(readLineageViewport('ds.github.repo.v1')).toEqual(DEFAULT_VIEWPORT)
})

it('returns default viewport for non-finite values', () => {
  window.localStorage.setItem(
    'lineage-viewport-ds.github.repo.v1',
    JSON.stringify({ x: Number.NaN, y: 0, zoom: 1 }),
  )

  expect(readLineageViewport('ds.github.repo.v1')).toEqual(DEFAULT_VIEWPORT)
})

it('returns default viewport for extreme coordinates', () => {
  window.localStorage.setItem(
    'lineage-viewport-ds.github.repo.v1',
    JSON.stringify({ x: 999999, y: 0, zoom: 1 }),
  )

  expect(readLineageViewport('ds.github.repo.v1')).toEqual(DEFAULT_VIEWPORT)
})
