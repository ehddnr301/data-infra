import type { AiManifestEntry, DomainName } from '@pseudolab/shared-types'
import { Hono } from 'hono'
import type { AuthEnv } from '../../middleware/user-auth'
import { requireUserAuth } from '../../middleware/user-auth'
import { PREVIEW_SOURCE_BY_DATASET_ID } from '../catalog/preview-sources'

const MANIFEST_CACHE_KEY = 'ai:manifest:v2'
const MANIFEST_CACHE_TTL = 3600 // 1 hour

const aiRouter = new Hono<AuthEnv>()
aiRouter.use('*', requireUserAuth)

aiRouter.get('/manifest', async (c) => {
  // 1. Check KV cache
  const cached = await c.env.CACHE.get<{ success: true; data: AiManifestEntry[] }>(
    MANIFEST_CACHE_KEY,
    'json',
  )
  if (cached) {
    return c.json(cached)
  }

  // 2. Fetch all datasets
  const datasetsResult = await c.env.DB.prepare(
    'SELECT id, domain, name, purpose FROM catalog_datasets ORDER BY domain, name',
  ).all<{ id: string; domain: DomainName; name: string; purpose: string | null }>()

  // 3. Fetch column counts per dataset
  const colCountResult = await c.env.DB.prepare(
    'SELECT dataset_id, COUNT(*) as cnt FROM catalog_columns GROUP BY dataset_id',
  ).all<{ dataset_id: string; cnt: number }>()

  const colCountMap = new Map<string, number>()
  for (const row of colCountResult.results) {
    colCountMap.set(row.dataset_id, row.cnt)
  }

  // 4. Fetch PII datasets
  const piiResult = await c.env.DB.prepare(
    'SELECT DISTINCT dataset_id FROM catalog_columns WHERE is_pii = 1',
  ).all<{ dataset_id: string }>()

  const piiSet = new Set(piiResult.results.map((r) => r.dataset_id))

  // 5. Batch query row_count + freshness for all preview sources
  const previewEntries = Object.entries(PREVIEW_SOURCE_BY_DATASET_ID)
  const batchStatements = previewEntries.map(([, { table, sortCol }]) =>
    c.env.DB.prepare(`SELECT MAX(rowid) as approx_rows, MAX(${sortCol}) as latest FROM ${table}`),
  )

  const rowFreshnessMap = new Map<string, { row_count: number; freshness: string | null }>()

  if (batchStatements.length > 0) {
    const batchResults = await c.env.DB.batch(batchStatements)
    for (let i = 0; i < previewEntries.length; i++) {
      const entry = previewEntries[i]
      if (!entry) continue
      const [datasetId] = entry
      const result = batchResults[i] as {
        results: Array<{ approx_rows: number | null; latest: string | null }>
      }
      const row = result.results[0]
      rowFreshnessMap.set(datasetId, {
        row_count: row?.approx_rows ?? 0,
        freshness: row?.latest ?? null,
      })
    }
  }

  // 6. Assemble manifest
  const manifest: AiManifestEntry[] = datasetsResult.results.map((ds) => {
    const stats = rowFreshnessMap.get(ds.id)
    const previewSource = PREVIEW_SOURCE_BY_DATASET_ID[ds.id]
    return {
      dataset_id: ds.id,
      domain: ds.domain,
      name: ds.name,
      table_name: previewSource?.table ?? null,
      purpose: ds.purpose,
      column_count: colCountMap.get(ds.id) ?? 0,
      row_count: stats?.row_count ?? 0,
      freshness: stats?.freshness ?? null,
      has_pii: piiSet.has(ds.id),
    }
  })

  const response = { success: true as const, data: manifest }

  // 7. Cache to KV
  await c.env.CACHE.put(MANIFEST_CACHE_KEY, JSON.stringify(response), {
    expirationTtl: MANIFEST_CACHE_TTL,
  })

  return c.json(response)
})

export default aiRouter
