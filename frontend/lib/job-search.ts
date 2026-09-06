import type { JobSearchParams } from './api/jobs'

export type SearchValues = Record<string, string | string[] | undefined>

export function parseJobSearch(values: SearchValues): JobSearchParams {
  const one = (key: string) => typeof values[key] === 'string' ? (values[key] as string).trim() : ''
  const page = Number(one('page'))
  const days = Number(one('min_posted_days'))
  return {
    q: one('q').slice(0, 100) || undefined,
    location: one('location').slice(0, 100) || undefined,
    source: one('source').slice(0, 50) || undefined,
    remote_type: ['remote', 'hybrid', 'onsite'].includes(one('remote_type')) ? one('remote_type') : undefined,
    min_posted_days: [1, 7, 30].includes(days) ? days : undefined,
    page: Number.isSafeInteger(page) && page > 0 && page <= 10000 ? page : 1,
    page_size: 20,
  }
}

export function jobSearchQuery(params: JobSearchParams): string {
  const query = new URLSearchParams()
  for (const key of ['q', 'location', 'source', 'remote_type', 'min_posted_days', 'page'] as const) {
    const value = params[key]
    if (value && !(key === 'page' && value === 1)) query.set(key, String(value))
  }
  return query.toString()
}

export function jobSearchHref(params: JobSearchParams): string {
  const query = jobSearchQuery(params)
  return `/jobs${query ? `?${query}` : ''}`
}
