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
