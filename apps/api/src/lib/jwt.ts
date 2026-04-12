export type JwtPayload = {
  email: string
  name: string
  role: 'pending' | 'member' | 'admin'
  picture: string | null
  iat: number
  exp: number
}

const HEADER = { alg: 'HS256', typ: 'JWT' }
const JWT_TTL_SECONDS = 7 * 24 * 60 * 60 // 7 days

function base64UrlEncode(data: Uint8Array): string {
  let binary = ''
  for (const byte of data) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function base64UrlEncodeString(str: string): string {
  return base64UrlEncode(new TextEncoder().encode(str))
}

function base64UrlDecode(str: string): string {
  const padded =
    str.replace(/-/g, '+').replace(/_/g, '/') + '=='.slice(0, (4 - (str.length % 4)) % 4)
  return atob(padded)
}

async function importKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign', 'verify'],
  )
}

export async function signJwt(
  payload: Omit<JwtPayload, 'iat' | 'exp'>,
  secret: string,
): Promise<string> {
  const now = Math.floor(Date.now() / 1000)
  const fullPayload: JwtPayload = { ...payload, iat: now, exp: now + JWT_TTL_SECONDS }

  const headerB64 = base64UrlEncodeString(JSON.stringify(HEADER))
  const payloadB64 = base64UrlEncodeString(JSON.stringify(fullPayload))
  const signingInput = `${headerB64}.${payloadB64}`

  const key = await importKey(secret)
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(signingInput))

  return `${signingInput}.${base64UrlEncode(new Uint8Array(signature))}`
}

export async function verifyJwt(token: string, secret: string): Promise<JwtPayload | null> {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null

    const [headerB64, payloadB64, signatureB64] = parts as [string, string, string]
    const signingInput = `${headerB64}.${payloadB64}`

    const key = await importKey(secret)
    const signatureBytes = Uint8Array.from(base64UrlDecode(signatureB64), (c) => c.charCodeAt(0))

    const valid = await crypto.subtle.verify(
      'HMAC',
      key,
      signatureBytes,
      new TextEncoder().encode(signingInput),
    )
    if (!valid) return null

    const payload = JSON.parse(base64UrlDecode(payloadB64)) as JwtPayload
    if (payload.exp < Math.floor(Date.now() / 1000)) return null

    return payload
  } catch {
    return null
  }
}
