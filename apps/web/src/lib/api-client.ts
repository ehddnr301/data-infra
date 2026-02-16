import type { ProblemDetail } from '@pseudolab/shared-types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8787'

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: ProblemDetail | null,
  ) {
    super(body?.detail ?? body?.title ?? `API error ${status}`)
    this.name = 'ApiError'
  }
}

type RequestOptions = {
  params?: Record<string, string | number | undefined>
}

export async function apiGet<T>(path: string, options?: RequestOptions): Promise<T> {
  const url = new URL(`/api${path}`, API_BASE)

  if (options?.params) {
    for (const [key, value] of Object.entries(options.params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value))
      }
    }
  }

  const res = await fetch(url.toString())

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, body)
  }

  return res.json() as Promise<T>
}
