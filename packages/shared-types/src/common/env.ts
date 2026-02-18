// Cloudflare runtime type stubs — avoids requiring @cloudflare/workers-types
// in every consuming package. Workers packages should use @cloudflare/workers-types directly.
/* eslint-disable @typescript-eslint/no-explicit-any */
type R2Bucket = any
type D1Database = any
type KVNamespace = any
/* eslint-enable @typescript-eslint/no-explicit-any */

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
