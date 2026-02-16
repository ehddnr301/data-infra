import { Hono } from 'hono'
import type { Env } from '@pseudolab/shared-types'

type CheckStatus = 'ok' | 'fail'

type ReadinessResult = {
  status: 'ok' | 'degraded' | 'unhealthy'
  timestamp: string
  checks: {
    d1: { status: CheckStatus; latencyMs?: number }
    r2: { status: CheckStatus; latencyMs?: number }
    kv: { status: CheckStatus; latencyMs?: number }
  }
}

const healthRouter = new Hono<{ Bindings: Env }>()

function nowIso(): string {
  return new Date().toISOString()
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return await Promise.race([
    promise,
    new Promise<T>((_, reject) => {
      setTimeout(() => reject(new Error('timeout')), timeoutMs)
    }),
  ])
}

async function probe(name: 'd1' | 'r2' | 'kv', env: Env): Promise<{ status: CheckStatus; latencyMs?: number }> {
  const start = Date.now()

  try {
    if (name === 'd1') {
      await withTimeout(env.DB.prepare('SELECT 1').first(), 2000)
    }

    if (name === 'r2') {
      await withTimeout(env.ARCHIVE_BUCKET.head('__health__'), 2000)
    }

    if (name === 'kv') {
      await withTimeout(env.CACHE.get('__health__'), 2000)
    }

    return { status: 'ok', latencyMs: Date.now() - start }
  } catch {
    return { status: 'fail', latencyMs: Date.now() - start }
  }
}

healthRouter.get('/', (c) => {
  return c.json(
    {
      status: 'ok',
      timestamp: nowIso(),
    },
    200,
    {
      'Content-Type': 'application/json; charset=utf-8',
    },
  )
})

healthRouter.get('/ready', async (c) => {
  const [d1, r2, kv] = await Promise.all([
    probe('d1', c.env),
    probe('r2', c.env),
    probe('kv', c.env),
  ])

  const failures = [d1, r2, kv].filter((check) => check.status === 'fail').length

  const status: ReadinessResult['status'] =
    failures === 0 ? 'ok' : failures === 3 ? 'unhealthy' : 'degraded'
  const statusCode = status === 'unhealthy' ? 503 : 200

  return c.json(
    {
      status,
      timestamp: nowIso(),
      checks: { d1, r2, kv },
    } satisfies ReadinessResult,
    statusCode,
    {
      'Content-Type': 'application/json; charset=utf-8',
    },
  )
})

export default healthRouter
