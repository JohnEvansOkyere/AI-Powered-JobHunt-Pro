import type { MetadataRoute } from 'next'

const SITE_URL = process.env.NEXT_PUBLIC_APP_URL || 'https://veloxahire.org'
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
      next: { revalidate: 3600 },
    })

    if (!response.ok) return []
    return (await response.json()) as JobSitemapEntry[]
  } catch {
    // Keep the core sitemap available if the jobs API is temporarily down.
    return []
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const corePages: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 1,
    },
    {
      url: `${SITE_URL}/jobs`,
      lastModified: new Date(),
      changeFrequency: 'hourly',
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/remote-jobs`,
      lastModified: new Date(),
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

  const jobs = await getJobEntries()
  const jobPages: MetadataRoute.Sitemap = jobs.map((job) => ({
    url: `${SITE_URL}/jobs/${job.id}`,
    lastModified: job.updated_at,
    changeFrequency: 'daily',
    priority: 0.7,
  }))

  return [...corePages, ...jobPages]
}
