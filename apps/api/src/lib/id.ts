const ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-'

export function nanoid(size = 21): string {
  const bytes = crypto.getRandomValues(new Uint8Array(size))
  let id = ''
  for (let i = 0; i < size; i++) {
    const byte = bytes[i] as number
    id += ALPHABET[byte & 63]
  }
  return id
}
