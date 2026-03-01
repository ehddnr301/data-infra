type R2Bucket = {
  head: (key: string) => Promise<unknown>
}

type KVGetType = 'text' | 'json' | 'arrayBuffer' | 'stream'

type KVNamespace = {
  get: <T = string>(key: string, type?: KVGetType) => Promise<T | null>
  put: (key: string, value: string, options?: { expirationTtl?: number }) => Promise<void>
}

type D1ResultMeta = {
  duration?: number
  changes?: number
  last_row_id?: number
  changed_db?: boolean
  size_after?: number
  rows_read?: number
  rows_written?: number
}

type D1ExecResult = {
  count: number
  duration: number
}

type D1RunResult = {
  success: boolean
  meta: D1ResultMeta
}

type D1AllResult<T = Record<string, unknown>> = {
  results: T[]
  success: boolean
  meta: D1ResultMeta
}

type D1PreparedStatement = {
  bind: (...values: unknown[]) => D1PreparedStatement
  first: <T = Record<string, unknown>>(column?: string) => Promise<T | null>
  all: <T = Record<string, unknown>>() => Promise<D1AllResult<T>>
  run: () => Promise<D1RunResult>
}

type D1Database = {
  prepare: (query: string) => D1PreparedStatement
  batch: <T = unknown>(statements: D1PreparedStatement[]) => Promise<T[]>
  exec: (query: string) => Promise<D1ExecResult>
}

export interface CoreBindings {
  ARCHIVE_BUCKET: R2Bucket
  DB: D1Database
  CACHE: KVNamespace
}

export interface RuntimeVars {
  ENVIRONMENT?: 'dev' | 'staging' | 'prod'
  LOG_LEVEL?: 'debug' | 'info' | 'warn' | 'error'
}

export type Env = CoreBindings & Partial<RuntimeVars>
