import type { Env } from '@pseudolab/shared-types'
import { Hono } from 'hono'
import { AppError, badRequest, internal, notFound } from '../lib/errors'
import { nanoid } from '../lib/id'
import { signJwt, verifyJwt } from '../lib/jwt'
import { extractBearerToken } from '../middleware/internal-auth'
import type { AuthEnv } from '../middleware/user-auth'
import { requireUserAuth } from '../middleware/user-auth'

const authRouter = new Hono<{ Bindings: Env }>()

const STATE_TTL = 600 // 10 minutes
const CODE_TTL = 60 // 1 minute
const PAT_PREFIX = 'plat_'

async function hashToken(token: string): Promise<string> {
  const data = new TextEncoder().encode(token)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, '0')).join('')
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function parseCookies(header: string | undefined): Record<string, string> {
  if (!header) return {}
  const cookies: Record<string, string> = {}
  for (const pair of header.split(';')) {
    const [key, ...rest] = pair.split('=')
    if (key) cookies[key.trim()] = rest.join('=').trim()
  }
  return cookies
}

// ---------------------------------------------------------------------------
// GET /api/auth/google — Initiate OAuth flow
// ---------------------------------------------------------------------------
authRouter.get('/google', async (c) => {
  const clientId = c.env.GOOGLE_CLIENT_ID?.trim()
  if (!clientId) {
    throw new AppError(
      503,
      'Service Unavailable',
      '/errors/service-unavailable',
      'GOOGLE_CLIENT_ID is not configured',
    )
  }

  // Generate CSRF state token
  const stateBytes = crypto.getRandomValues(new Uint8Array(16))
  const state = Array.from(stateBytes, (b) => b.toString(16).padStart(2, '0')).join('')

  // Store in KV for server-side validation
  await c.env.CACHE.put(`oauth_state:${state}`, '1', { expirationTtl: STATE_TTL })

  const redirectUri = new URL('/api/auth/google/callback', c.req.url).toString()

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: 'openid email profile',
    state,
    access_type: 'online',
    prompt: 'consent',
  })

  // [Review Fix 1] Bind state to browser session via HttpOnly cookie
  const isSecure = new URL(c.req.url).protocol === 'https:'
  const cookieFlags = `HttpOnly; SameSite=Lax; Path=/api/auth; Max-Age=${STATE_TTL}${isSecure ? '; Secure' : ''}`

  return new Response(null, {
    status: 302,
    headers: {
      Location: `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`,
      'Set-Cookie': `oauth_state=${state}; ${cookieFlags}`,
    },
  })
})

// ---------------------------------------------------------------------------
// GET /api/auth/google/callback — Exchange code, validate, issue one-time code
// ---------------------------------------------------------------------------
authRouter.get('/google/callback', async (c) => {
  const code = c.req.query('code')
  const state = c.req.query('state')
  const error = c.req.query('error')

  if (error) {
    throw badRequest(`Google OAuth error: ${error}`)
  }
  if (!code || !state) {
    throw badRequest('Missing code or state parameter')
  }

  // [Review Fix 1] Validate state against both KV and browser cookie
  const storedState = await c.env.CACHE.get(`oauth_state:${state}`)
  if (!storedState) {
    throw new AppError(403, 'Forbidden', '/errors/forbidden', 'Invalid or expired OAuth state')
  }

  const cookies = parseCookies(c.req.header('Cookie'))
  if (cookies.oauth_state !== state) {
    throw new AppError(
      403,
      'Forbidden',
      '/errors/forbidden',
      'OAuth state mismatch with browser session',
    )
  }

  // Consume the state (prevent replay)
  await c.env.CACHE.put(`oauth_state:${state}`, '', { expirationTtl: 60 })

  // Exchange code for tokens
  const clientId = c.env.GOOGLE_CLIENT_ID?.trim()
  const clientSecret = c.env.GOOGLE_CLIENT_SECRET?.trim()
  const jwtSecret = c.env.JWT_SECRET?.trim()
  if (!clientId || !clientSecret || !jwtSecret) {
    throw internal('OAuth secrets not configured')
  }

  const redirectUri = new URL('/api/auth/google/callback', c.req.url).toString()

  const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: clientId,
      client_secret: clientSecret,
      code,
      redirect_uri: redirectUri,
      grant_type: 'authorization_code',
    }),
  })

  if (!tokenRes.ok) {
    const detail = await tokenRes.text().catch(() => 'unknown')
    throw internal(`Google token exchange failed: ${detail}`)
  }

  const tokenData = (await tokenRes.json()) as { id_token?: string }
  if (!tokenData.id_token) {
    throw internal('No id_token in Google response')
  }

  // Decode id_token payload
  const payloadB64 = tokenData.id_token.split('.')[1]
  if (!payloadB64) {
    throw internal('Malformed id_token')
  }
  const padded =
    payloadB64.replace(/-/g, '+').replace(/_/g, '/') +
    '=='.slice(0, (4 - (payloadB64.length % 4)) % 4)
  const binaryStr = atob(padded)
  const bytes = Uint8Array.from(binaryStr, (c) => c.charCodeAt(0))
  const idPayload = JSON.parse(new TextDecoder().decode(bytes)) as {
    email?: string
    name?: string
    picture?: string
    aud?: string
    iss?: string
    exp?: number
    email_verified?: boolean
  }

  // [Review Fix 3] Validate id_token claims
  if (idPayload.aud !== clientId) {
    throw internal('id_token aud mismatch')
  }
  if (idPayload.iss !== 'https://accounts.google.com' && idPayload.iss !== 'accounts.google.com') {
    throw internal('id_token iss mismatch')
  }
  if (idPayload.exp && idPayload.exp < Math.floor(Date.now() / 1000)) {
    throw internal('id_token expired')
  }
  if (idPayload.email_verified !== true) {
    throw badRequest('Email is not verified by Google')
  }

  const email = idPayload.email
  if (!email) {
    throw internal('No email in id_token')
  }
  const name = idPayload.name ?? ''
  const picture = idPayload.picture ?? null

  // Upsert user in D1
  await c.env.DB.prepare(
    `INSERT INTO users (email, name, picture, role, last_login_at)
     VALUES (?, ?, ?, 'member', datetime('now'))
     ON CONFLICT(email) DO UPDATE SET
       name = excluded.name,
       picture = excluded.picture,
       last_login_at = datetime('now')`,
  )
    .bind(email, name, picture)
    .run()

  // Get current role
  const user = await c.env.DB.prepare('SELECT role FROM users WHERE email = ?')
    .bind(email)
    .first<{ role: 'pending' | 'member' | 'admin' }>()

  const role = user?.role ?? 'member'

  // Sign JWT
  const jwt = await signJwt({ email, name, role, picture }, jwtSecret)

  // [Review Fix 2] Store JWT behind a one-time code instead of passing in URL
  const oneTimeCode = nanoid()
  await c.env.CACHE.put(`auth_code:${oneTimeCode}`, JSON.stringify({ jwt, email, name, role }), {
    expirationTtl: CODE_TTL,
  })

  // Redirect to frontend with code only (no JWT in URL)
  const frontendUrl = c.env.FRONTEND_URL?.trim() || new URL('/', c.req.url).origin
  const callbackUrl = new URL('/auth/callback', frontendUrl)
  callbackUrl.searchParams.set('code', oneTimeCode)

  // Clear the state cookie
  const isSecure = new URL(c.req.url).protocol === 'https:'
  const clearCookieFlags = `HttpOnly; SameSite=Lax; Path=/api/auth; Max-Age=0${isSecure ? '; Secure' : ''}`

  return new Response(null, {
    status: 302,
    headers: {
      Location: callbackUrl.toString(),
      'Set-Cookie': `oauth_state=; ${clearCookieFlags}`,
    },
  })
})

// ---------------------------------------------------------------------------
// POST /api/auth/exchange — Exchange one-time code for JWT
// ---------------------------------------------------------------------------
authRouter.post('/exchange', async (c) => {
  const body = (await c.req.json().catch(() => null)) as { code?: string } | null
  const code = body?.code?.trim()
  if (!code) {
    throw badRequest('Missing code')
  }

  const stored = await c.env.CACHE.get(`auth_code:${code}`)
  if (!stored) {
    throw new AppError(401, 'Unauthorized', '/errors/unauthorized', 'Invalid or expired code')
  }

  // Consume the code (prevent replay)
  await c.env.CACHE.put(`auth_code:${code}`, '', { expirationTtl: 60 })

  const data = JSON.parse(stored) as { jwt: string; email: string; name: string; role: string }

  return c.json({
    success: true,
    data: {
      token: data.jwt,
      email: data.email,
      name: data.name,
      role: data.role,
    },
  })
})

// ---------------------------------------------------------------------------
// GET /api/auth/me — Return current user info from JWT
// ---------------------------------------------------------------------------
authRouter.get('/me', async (c) => {
  const jwtSecret = c.env.JWT_SECRET?.trim()
  if (!jwtSecret) {
    throw internal('JWT_SECRET not configured')
  }

  const token = extractBearerToken(c.req.header('Authorization'))
  if (!token) {
    throw new AppError(401, 'Unauthorized', '/errors/unauthorized', 'Missing bearer token')
  }

  const payload = await verifyJwt(token, jwtSecret)
  if (!payload) {
    throw new AppError(401, 'Unauthorized', '/errors/unauthorized', 'Invalid or expired token')
  }

  // Get latest role from D1 (may have changed since JWT was issued)
  const user = await c.env.DB.prepare(
    'SELECT email, name, picture, role, created_at, approved_at FROM users WHERE email = ?',
  )
    .bind(payload.email)
    .first<{
      email: string
      name: string | null
      picture: string | null
      role: string
      created_at: string
      approved_at: string | null
    }>()

  if (!user) {
    throw new AppError(401, 'Unauthorized', '/errors/unauthorized', 'User not found')
  }

  return c.json({
    success: true,
    data: {
      email: user.email,
      name: user.name ?? '',
      picture: user.picture,
      role: user.role,
      created_at: user.created_at,
      approved_at: user.approved_at,
    },
  })
})

// ---------------------------------------------------------------------------
// Personal API Tokens (PAT) — requires JWT auth
// ---------------------------------------------------------------------------
const tokenRouter = new Hono<AuthEnv>()
tokenRouter.use('*', requireUserAuth)

// POST /api/auth/tokens — Create a new PAT
tokenRouter.post('/', async (c) => {
  const user = c.get('user')
  const body = (await c.req.json().catch(() => null)) as {
    name?: string
    display_name?: string
  } | null
  const tokenName = body?.name?.trim()
  if (!tokenName) {
    throw badRequest('Token name is required')
  }
  const displayName = body?.display_name?.trim() || null

  const id = nanoid()
  const rawToken = `${PAT_PREFIX}${nanoid(32)}`
  const tokenHash = await hashToken(rawToken)
  const tokenPrefix = rawToken.slice(0, 12)

  await c.env.DB.prepare(
    'INSERT INTO user_api_tokens (id, user_email, name, token_hash, token_prefix, display_name) VALUES (?, ?, ?, ?, ?, ?)',
  )
    .bind(id, user.email, tokenName, tokenHash, tokenPrefix, displayName)
    .run()

  return c.json({
    success: true,
    data: {
      id,
      name: tokenName,
      display_name: displayName,
      token: rawToken,
      token_prefix: tokenPrefix,
      created_at: new Date().toISOString(),
    },
  })
})

// GET /api/auth/tokens — List user's PATs (without full token)
tokenRouter.get('/', async (c) => {
  const user = c.get('user')
  const rows = await c.env.DB.prepare(
    'SELECT id, name, token_prefix, created_at, last_used_at FROM user_api_tokens WHERE user_email = ? ORDER BY created_at DESC',
  )
    .bind(user.email)
    .all<{
      id: string
      name: string
      token_prefix: string
      created_at: string
      last_used_at: string | null
    }>()

  return c.json({ success: true, data: rows.results })
})

// DELETE /api/auth/tokens/:id — Revoke a PAT
tokenRouter.delete('/:id', async (c) => {
  const user = c.get('user')
  const tokenId = c.req.param('id')

  const existing = await c.env.DB.prepare(
    'SELECT id FROM user_api_tokens WHERE id = ? AND user_email = ?',
  )
    .bind(tokenId, user.email)
    .first()

  if (!existing) {
    throw notFound('Token not found')
  }

  await c.env.DB.prepare('DELETE FROM user_api_tokens WHERE id = ?').bind(tokenId).run()

  return c.json({ success: true })
})

authRouter.route('/tokens', tokenRouter)

export default authRouter
