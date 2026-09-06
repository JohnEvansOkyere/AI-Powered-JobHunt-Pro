/** Canonical public origin; normalizes the apex to the host served in production. */
export function canonicalOrigin(value = process.env.NEXT_PUBLIC_APP_URL): string {
  const url = new URL(value || 'https://www.veloxahire.org')
  if (url.hostname === 'veloxahire.org' || url.hostname === 'www.veloxahire.org') {
    url.hostname = 'www.veloxahire.org'
    url.protocol = 'https:'
    url.port = ''
  }
  return url.origin
}

export const SITE_URL = canonicalOrigin()

/** Prevent untrusted strings from terminating a JSON-LD script element. */
export function serializeJsonLd(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026')
}
