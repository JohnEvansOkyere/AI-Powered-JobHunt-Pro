import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ArrowLeft, ArrowRight, Bookmark, Briefcase, Building2, Clock, MapPin, Sparkles } from 'lucide-react'
import type { Job } from '@/lib/api/jobs'
import { cleanJobDescription } from '@/lib/text'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
const SITE_URL = process.env.NEXT_PUBLIC_APP_URL || 'https://veloxahire.org'

async function getJob(id: string): Promise<Job | null> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${id}`, {
    cache: 'no-store',
  })

  if (response.status === 404) return null
  if (!response.ok) throw new Error('Failed to load job')
  return response.json()
}

function formatDate(dateString?: string | null) {
  if (!dateString) return 'Recently posted'
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return 'Recently posted'
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

function applyHref(job: Job) {
  return job.job_link || job.source_url || ''
}

function isIndexableJob(job: Job) {
  return Boolean(
    job.processing_status === 'processed' &&
      job.posted_date &&
      job.title.trim() &&
      job.company.trim() &&
      cleanJobDescription(job.description).trim() &&
      applyHref(job),
  )
}

function serializeJsonLd(value: unknown) {
  return JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const job = await getJob(params.id)
  if (!job) {
    return {
      title: 'Job Not Found | VeloxaHire',
    }
  }

  const title = `${job.title} at ${job.company} | VeloxaHire`
  const description = cleanJobDescription(job.description).slice(0, 155)
  const indexable = isIndexableJob(job)
  return {
    title,
    description,
    alternates: {
      canonical: `/jobs/${job.id}`,
    },
    robots: indexable ? undefined : { index: false, follow: true },
    openGraph: {
      title,
      description,
      type: 'article',
      url: `${SITE_URL}/jobs/${job.id}`,
      images: [
        {
          url: '/og-image.png',
          width: 1200,
          height: 630,
          alt: 'VeloxaRecruit — AI-Powered Recruitment',
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      images: ['/og-image.png'],
    },
  }
}

export default async function JobDetailPage({ params }: { params: { id: string } }) {
  const job = await getJob(params.id)
  if (!job) notFound()

  const applyUrl = applyHref(job)
  const postedDate = job.posted_date || job.scraped_at
  const indexable = isIndexableJob(job)
  const remoteType = (job.remote_type || job.remote_option || '').toLowerCase()
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'JobPosting',
    title: job.title,
    description: cleanJobDescription(job.description),
    datePosted: job.posted_date,
    employmentType: job.job_type || undefined,
    hiringOrganization: {
      '@type': 'Organization',
      name: job.company,
    },
    jobLocation: job.location
      ? {
          '@type': 'Place',
          address: {
            '@type': 'PostalAddress',
            addressLocality: job.location,
          },
        }
      : undefined,
    jobLocationType: remoteType.includes('remote') ? 'TELECOMMUTE' : undefined,
    url: `${SITE_URL}/jobs/${job.id}`,
  }

  return (
    <main className="min-h-screen bg-cream-50 text-ink-900">
      {indexable && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
        />
      )}
      <header className="border-b border-ink-900/10 bg-forest-700 text-cream-100">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between gap-4">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            Veloxa<span className="text-ember-300">Hire</span>
          </Link>
          <Link href="/auth/signup" className="inline-flex items-center gap-1.5 rounded-full bg-cream-100 px-4 py-2 text-sm font-semibold text-ink-900 hover:bg-cream-50">
            Get recommendations
            <Sparkles className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      <article className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <Link href="/jobs" className="mb-6 inline-flex items-center gap-1.5 text-sm font-semibold text-neutral-500 hover:text-neutral-900">
          <ArrowLeft className="h-4 w-4" />
          Back to jobs
        </Link>

        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <section className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {job.source === 'recruiter' && (
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                  Direct recruiter role
                </span>
              )}
              <span className="rounded-full bg-neutral-100 px-2 py-1 text-xs font-semibold text-neutral-500">
                {formatDate(postedDate)}
              </span>
            </div>

            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-neutral-900">
              {job.title}
            </h1>
            <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-neutral-500">
              <span className="inline-flex items-center gap-1.5">
                <Building2 className="h-4 w-4" />
                {job.company}
              </span>
              {job.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-4 w-4" />
                  {job.location}
                </span>
              )}
              {job.job_type && (
                <span className="inline-flex items-center gap-1.5 capitalize">
                  <Briefcase className="h-4 w-4" />
                  {job.job_type}
                </span>
              )}
              <span className="inline-flex items-center gap-1.5">
                <Clock className="h-4 w-4" />
                {formatDate(postedDate)}
              </span>
            </div>

            <div className="mt-8 border-t border-neutral-100 pt-8">
              <h2 className="text-lg font-semibold text-neutral-900">Job description</h2>
              <div className="mt-4 whitespace-pre-line text-sm leading-7 text-neutral-700">
                {cleanJobDescription(job.description)}
              </div>
            </div>

            {job.requirements && (
              <div className="mt-8 border-t border-neutral-100 pt-8">
                <h2 className="text-lg font-semibold text-neutral-900">Requirements</h2>
                <div className="mt-4 whitespace-pre-line text-sm leading-7 text-neutral-700">
                  {cleanJobDescription(job.requirements)}
                </div>
              </div>
            )}
          </section>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
              {applyUrl ? (
                <a
                  href={applyUrl}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-neutral-900 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800"
                >
                  Apply now
                  <ArrowRight className="h-4 w-4" />
                </a>
              ) : (
                <p className="rounded-xl bg-neutral-100 px-4 py-3 text-center text-sm font-semibold text-neutral-500">
                  Apply link unavailable
                </p>
              )}
              <p className="mt-3 text-xs leading-relaxed text-neutral-500">
                Applications open on the employer or recruiter page. Create a profile afterwards to track roles and get similar jobs.
              </p>
            </div>

            <div className="rounded-2xl border border-brand-turquoise-100 bg-brand-turquoise-50 p-5">
              <Bookmark className="h-5 w-5 text-brand-turquoise-700" />
              <h2 className="mt-3 font-semibold text-neutral-900">Get roles like this ranked for you</h2>
              <p className="mt-2 text-sm leading-relaxed text-neutral-600">
                Upload your CV once and VeloxaHire will score matching jobs, save your shortlist, and keep track of applications.
              </p>
              <Link href="/auth/signup" className="mt-4 inline-flex w-full items-center justify-center rounded-xl bg-brand-turquoise-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-turquoise-700">
                Create free profile
              </Link>
            </div>
          </aside>
        </div>
      </article>
    </main>
  )
}
