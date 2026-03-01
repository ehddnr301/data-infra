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

type JsonBody = Record<string, unknown>

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

async function requestWithBody<T>(
  method: 'POST' | 'PUT' | 'DELETE',
  path: string,
  body?: JsonBody,
): Promise<T> {
  const url = new URL(`/api${path}`, API_BASE)
  const res = await fetch(url.toString(), {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })

  if (!res.ok) {
    const payload = await res.json().catch(() => null)
    throw new ApiError(res.status, payload)
  }

  return res.json() as Promise<T>
}

export function apiPost<T>(path: string, body: JsonBody): Promise<T> {
  return requestWithBody<T>('POST', path, body)
}

export function apiPut<T>(path: string, body: JsonBody): Promise<T> {
  return requestWithBody<T>('PUT', path, body)
}

export function apiDelete<T>(path: string): Promise<T> {
  return requestWithBody<T>('DELETE', path)
}
