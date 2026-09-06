import type { MetadataRoute } from 'next'
import { SITE_URL } from '@/lib/site'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

// Job inventory changes after deployment, so generate the sitemap on request
// instead of freezing the job list into the Next.js build output.
export const dynamic = 'force-dynamic'

type JobSitemapEntry = {
  id: string
  updated_at: string
}

async function getJobEntries(): Promise<JobSitemapEntry[]> {
  try {
    const response = await fetch(`${API_URL}/api/v1/jobs/sitemap`, {
      cache: 'no-store', signal: AbortSignal.timeout(8000),
    })

    if (!response.ok) { console.warn('seo.sitemap.fetch_failed', { status: response.status }); return [] }
    const jobs = await response.json()
    if (!Array.isArray(jobs)) throw new Error('Invalid sitemap response')
    return (jobs as JobSitemapEntry[]).filter(job => /^[0-9a-f-]{36}$/i.test(job.id) && Number.isFinite(Date.parse(job.updated_at)))
  } catch {
    // Keep the core sitemap available if the jobs API is temporarily down.
    console.warn('seo.sitemap.fetch_unavailable')
    return []
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const corePages: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      changeFrequency: 'weekly',
      priority: 1,
    },
    {
      url: `${SITE_URL}/jobs`,
      changeFrequency: 'hourly',
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/remote-jobs`,
      changeFrequency: 'hourly',
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/privacy`,
      changeFrequency: 'yearly',
      priority: 0.2,
    },
    {
      url: `${SITE_URL}/terms`,
      changeFrequency: 'yearly',
      priority: 0.2,
    },
  ]

  for (const path of ['/ghana-jobs', '/about', '/how-it-works', '/job-sources', '/contact', '/guides/remote-jobs-from-ghana']) {
    corePages.push({ url: `${SITE_URL}${path}`, changeFrequency: path === '/ghana-jobs' ? 'daily' : 'monthly', priority: 0.6 })
  }

  const jobs = await getJobEntries()
  const jobPages: MetadataRoute.Sitemap = jobs.map((job) => ({
    url: `${SITE_URL}/jobs/${job.id}`,
    lastModified: job.updated_at,
    changeFrequency: 'daily',
    priority: 0.7,
  }))

  return [...corePages, ...jobPages]
}
