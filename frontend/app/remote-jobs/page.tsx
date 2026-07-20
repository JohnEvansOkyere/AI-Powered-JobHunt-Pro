import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight, Briefcase, Globe2, MapPin, Sparkles } from 'lucide-react'
import type { Job, JobSearchResponse } from '@/lib/api/jobs'
import { cleanJobDescription } from '@/lib/text'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Remote Jobs | VeloxaHire',
  description:
    'Browse current remote jobs from recruiter and public job sources. Check location, time-zone, and application details before you apply.',
  alternates: {
    canonical: '/remote-jobs',
  },
}

function applyHref(job: Job) {
  return job.job_link || job.source_url || ''
}

function postedLabel(value?: string | null) {
  if (!value) return 'Recently posted'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Recently posted'
  return `Posted ${new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)}`
}

async function getRemoteJobs(): Promise<Job[]> {
  try {
    const response = await fetch(
      `${API_URL}/api/v1/jobs/?remote_type=remote&page=1&page_size=12`,
      { cache: 'no-store' },
    )

    if (!response.ok) return []
    const data = (await response.json()) as JobSearchResponse
    return data.jobs.filter(
      (job) =>
        job.processing_status === 'processed' &&
        Boolean(job.title.trim()) &&
        Boolean(job.company.trim()) &&
        Boolean(cleanJobDescription(job.description).trim()) &&
        Boolean(applyHref(job)),
    )
  } catch {
    return []
  }
}

function RemoteJobCard({ job }: { job: Job }) {
  const description = cleanJobDescription(job.description)

  return (
    <article className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-brand-turquoise-300 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-turquoise-700">
            Remote role
          </p>
          <h2 className="mt-2 text-xl font-semibold leading-snug text-neutral-900">
            <Link href={`/jobs/${job.id}`} className="hover:text-brand-turquoise-700">
              {job.title}
            </Link>
          </h2>
          <p className="mt-1 text-sm font-medium text-neutral-600">{job.company}</p>
        </div>
        <Globe2 className="mt-1 h-5 w-5 shrink-0 text-brand-turquoise-600" />
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-xs text-neutral-600">
        <span className="inline-flex items-center gap-1 rounded-md bg-neutral-100 px-2 py-1">
          <MapPin className="h-3 w-3 text-neutral-400" />
          {job.location || 'Location not specified'}
        </span>
        {job.job_type && (
          <span className="inline-flex items-center gap-1 rounded-md bg-neutral-100 px-2 py-1">
            <Briefcase className="h-3 w-3 text-neutral-400" />
            {job.job_type}
          </span>
        )}
        <span className="rounded-md bg-neutral-100 px-2 py-1">
          {postedLabel(job.posted_date || job.scraped_at)}
        </span>
      </div>

      <p className="mt-4 line-clamp-3 text-sm leading-6 text-neutral-600">{description}</p>

      <div className="mt-5 flex items-center gap-3">
        <Link
          href={`/jobs/${job.id}`}
          className="inline-flex items-center gap-1.5 rounded-xl bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800"
        >
          View details
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <a
          href={applyHref(job)}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="text-sm font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800"
        >
          Apply externally
        </a>
      </div>
    </article>
  )
}

export default async function RemoteJobsPage() {
  const jobs = await getRemoteJobs()

  return (
    <main className="min-h-screen bg-cream-50 text-ink-900">
      <header className="bg-forest-700 text-cream-100">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            Veloxa<span className="text-ember-300">Hire</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/jobs" className="text-sm text-cream-100/75 hover:text-cream-100">
              All jobs
            </Link>
            <Link
              href="/auth/signup"
              className="inline-flex items-center gap-1.5 rounded-full bg-cream-100 px-4 py-2 text-sm font-semibold text-ink-900 hover:bg-cream-50"
            >
              Get recommendations
              <Sparkles className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      <section className="border-b border-ink-900/10 bg-forest-700 px-4 pb-14 pt-8 text-cream-100 sm:px-6">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-medium text-ember-300">Remote job search</p>
          <h1 className="mt-3 max-w-3xl font-display text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
            Remote jobs for the next step in your career.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-cream-100/75">
            Explore current remote roles in one place. Open each listing to check the employer,
            location, eligibility, and application instructions before you spend time applying.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              href="/jobs"
              className="inline-flex items-center gap-2 rounded-full bg-cream-100 px-5 py-3 text-sm font-semibold text-ink-900 hover:bg-cream-50"
            >
              Browse all jobs
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/auth/signup"
              className="inline-flex items-center gap-2 rounded-full border border-cream-100/30 px-5 py-3 text-sm font-semibold text-cream-100 hover:bg-cream-100/10"
            >
              Get a CV-matched shortlist
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-turquoise-700">
              Current listings
            </p>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-neutral-900">
              Remote roles worth a closer look
            </h2>
          </div>
          <Link href="/jobs" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800">
            Search the full catalogue
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {jobs.length > 0 ? (
          <div className="mt-7 grid gap-4 lg:grid-cols-2">
            {jobs.map((job) => <RemoteJobCard key={job.id} job={job} />)}
          </div>
        ) : (
          <div className="mt-7 rounded-2xl border border-dashed border-neutral-300 bg-white p-8 text-center">
            <h2 className="font-semibold text-neutral-900">Remote listings are refreshing</h2>
            <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-neutral-600">
              Browse the full catalogue while the latest remote roles load, or create a profile so
              VeloxaHire can surface relevant roles as they arrive.
            </p>
          </div>
        )}
      </section>

      <section className="border-y border-ink-900/10 bg-cream-100 px-4 py-12 sm:px-6">
        <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1fr_1.2fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-turquoise-700">
              Before you apply
            </p>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-neutral-900">
              “Remote” does not always mean worldwide.
            </h2>
          </div>
          <div className="space-y-4 text-sm leading-7 text-neutral-700">
            <p>
              Some employers limit remote work to a country, region, or time zone. Check the full
              listing for work-authorisation requirements, expected working hours, and whether the
              employer can hire where you live.
            </p>
            <p>
              Job availability changes quickly. VeloxaHire links you to the original employer or
              source application page, so confirm that the role is still open before submitting your
              information.
            </p>
            <p>
              Want less searching? Upload your CV and create a free profile for personalized matches,
              saved jobs, and application tracking.
            </p>
          </div>
        </div>
      </section>
    </main>
  )
}
