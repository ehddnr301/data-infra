type R2Bucket = unknown
type D1Database = unknown
type KVNamespace = unknown

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
