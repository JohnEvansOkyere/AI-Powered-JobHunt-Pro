import { cache } from 'react'
import type { JobSearchResponse } from './api/jobs'

const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

/** Anonymous server fetch only: never forwards a candidate cookie or token. */
export const fetchPublicJobs = cache(async (query: string): Promise<JobSearchResponse | null> => {
  try {
    const response = await fetch(`${API_URL}/api/v1/jobs/?${query}`, {
      cache: 'no-store', signal: AbortSignal.timeout(8000),
    })
    if (!response.ok) {
      console.warn('seo.jobs.fetch_failed', { status: response.status })
      return null
    }
    const data = await response.json()
    if (!Array.isArray(data.jobs) || !Number.isFinite(data.total) || !Number.isFinite(data.total_pages)) throw new Error('Invalid public job response')
    return data as JobSearchResponse
  } catch {
    console.warn('seo.jobs.fetch_unavailable')
    return null
  }
})
