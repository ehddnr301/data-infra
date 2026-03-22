import { resolveApiBase } from '@/lib/api-client'

describe('resolveApiBase', () => {
  it('uses the configured VITE_API_URL when provided', () => {
    expect(
      resolveApiBase(
        'https://pseudolab-api.example.workers.dev',
        'https://master.pseudolab-web.pages.dev',
        'master.pseudolab-web.pages.dev',
      ),
    ).toBe('https://pseudolab-api.example.workers.dev')
  })

  it('falls back to the local API only on localhost', () => {
    expect(resolveApiBase(undefined, 'http://localhost:5173', 'localhost')).toBe(
      'http://localhost:8787',
    )
    expect(resolveApiBase(undefined, 'http://127.0.0.1:5173', '127.0.0.1')).toBe(
      'http://localhost:8787',
    )
  })

  it('uses the current origin outside local development when VITE_API_URL is absent', () => {
    expect(
      resolveApiBase(
        undefined,
        'https://master.pseudolab-web.pages.dev',
        'master.pseudolab-web.pages.dev',
      ),
    ).toBe('https://master.pseudolab-web.pages.dev')
  })
})
