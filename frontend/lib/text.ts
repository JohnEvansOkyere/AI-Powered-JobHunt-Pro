const BLOCK_TAG_RE = /<\s*\/?\s*(?:br|p|div|li|h[1-6]|ul|ol|section|article)\b[^>]*>/gi
const ENTITY_RE = /&(#x[\da-f]+|#\d+|[a-z][\da-z]+);/gi

const NAMED_ENTITIES: Record<string, string> = {
  amp: '&',
  apos: "'",
  gt: '>',
  lt: '<',
  nbsp: ' ',
  quot: '"',
}

function decodeHtmlEntities(value: string): string {
  return value.replace(ENTITY_RE, (_, entity: string) => {
    const lower = entity.toLowerCase()
    if (lower.startsWith('#x')) return String.fromCodePoint(parseInt(lower.slice(2), 16))
    if (lower.startsWith('#')) return String.fromCodePoint(parseInt(lower.slice(1), 10))
    return NAMED_ENTITIES[lower] ?? `&${entity};`
  })
}

/** Convert scraped HTML fragments into readable text for safe rendering. */
export function cleanJobDescription(value?: string | null): string {
  if (!value) return ''

  let text = decodeHtmlEntities(value).replace(/\0/g, '')
  text = text.replace(/<\s*(?:script|style)\b[^>]*>[\s\S]*?<\s*\/\s*(?:script|style)\s*>/gi, '')
  text = text.replace(BLOCK_TAG_RE, '\n')
  text = text.replace(/<[^>]*>/g, '')
  text = decodeHtmlEntities(text).replace(/\u00a0/g, ' ')
  text = text.replace(/[ \t\f\v]+/g, ' ')
  text = text.replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n')
  return text.trim()
}
