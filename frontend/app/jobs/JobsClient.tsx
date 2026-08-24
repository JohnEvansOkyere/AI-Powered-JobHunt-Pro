'use client'

import { useEffect, useMemo, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import {
  AlertCircle,
  ArrowRight,
  Bell,
  Bookmark,
  Briefcase,
  Banknote,
  Building2,
  Globe,
  MapPin,
  RefreshCw,
  Search,
  TrendingUp,
  X,
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import { searchJobs, type Job, type JobSearchParams } from '@/lib/api/jobs'
import { cleanJobDescription } from '@/lib/text'
import { useAuth } from '@/hooks/useAuth'
import { PostApplyModal } from '@/components/jobs/PostApplyModal'

const PAGE_SIZE = 20
const SIGNUP_PROMPT_DISMISSED_KEY = 'veloxahire:public-jobs-signup-prompt-dismissed'

type ViewMode = 'all' | 'recruiter'

function formatDate(dateString?: string | null) {
  if (!dateString) return 'Recently posted'
  const date = new Date(dateString)
  const diffDays = Math.floor((Date.now() - date.getTime()) / 86400000)
  if (diffDays <= 0) return 'Posted today'
  if (diffDays === 1) return 'Posted yesterday'
  if (diffDays < 7) return `Posted ${diffDays}d ago`
  if (diffDays < 30) return `Posted ${Math.floor(diffDays / 7)}w ago`
  return `Posted ${Math.floor(diffDays / 30)}mo ago`
}

function isNew(dateString?: string | null) {
  if (!dateString) return false
  const diffDays = Math.floor((Date.now() - new Date(dateString).getTime()) / 86400000)
  return diffDays <= 3
}

function jobApplyHref(job: Job) {
  return job.job_link || job.source_url || ''
}

function prettify(value?: string | null) {
  if (!value) return ''
  return value
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function salaryLabel(job: Job): string | null {
  if (job.salary_range) return job.salary_range
  const cur = job.salary_currency || ''
  if (job.salary_min && job.salary_max) return `${cur}${job.salary_min} – ${cur}${job.salary_max}`
  if (job.salary_min) return `From ${cur}${job.salary_min}`
  return null
}

function parseSkills(skills?: string | null): string[] {
  if (!skills) return []
  try {
    const parsed = JSON.parse(skills)
    if (Array.isArray(parsed)) return parsed.filter(Boolean).map(String)
  } catch {
    // fall back to comma-separated
    return skills.split(',').map((s) => s.trim()).filter(Boolean)
  }
  return []
}

// Deterministic on-brand avatar colour from the company name.
const AVATAR_STYLES = [
  'bg-brand-turquoise-100 text-brand-turquoise-800',
  'bg-emerald-100 text-emerald-800',
  'bg-amber-100 text-amber-800',
  'bg-indigo-100 text-indigo-800',
  'bg-rose-100 text-rose-800',
  'bg-forest-500/15 text-forest-700',
]
function avatarFor(name?: string | null) {
  const safe = (name || '?').trim()
  const initials = safe
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase() || '?'
  let hash = 0
  for (let i = 0; i < safe.length; i++) hash = (hash * 31 + safe.charCodeAt(i)) >>> 0
  return { initials, style: AVATAR_STYLES[hash % AVATAR_STYLES.length] }
}

function Chip({ icon: Icon, children }: { icon: typeof MapPin; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-neutral-100 px-2 py-1 text-xs font-medium text-neutral-600">
      <Icon className="h-3 w-3 text-neutral-400" />
      {children}
    </span>
  )
}

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-2xl border border-neutral-200 bg-white p-5">
      <div className="flex gap-4">
        <div className="h-11 w-11 shrink-0 rounded-xl bg-neutral-100" />
        <div className="min-w-0 flex-1">
          <div className="h-3 w-24 rounded bg-neutral-100" />
          <div className="mt-3 h-4 w-2/3 rounded bg-neutral-100" />
          <div className="mt-2 h-3 w-1/3 rounded bg-neutral-100" />
          <div className="mt-4 flex gap-2">
            <div className="h-6 w-20 rounded-md bg-neutral-100" />
            <div className="h-6 w-16 rounded-md bg-neutral-100" />
            <div className="h-6 w-24 rounded-md bg-neutral-100" />
          </div>
        </div>
      </div>
    </div>
  )
}

function JobCard({ job, saved, onSave }: { job: Job; saved: boolean; onSave: (id: string) => void }) {
  const avatar = avatarFor(job.company)
  const fresh = isNew(job.posted_date || job.scraped_at)
  const salary = salaryLabel(job)
  const skills = parseSkills(job.skills).slice(0, 4)
  const applyHref = jobApplyHref(job)

  return (
    <article className="group relative rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-turquoise-300 hover:shadow-md">
      <div className="flex gap-4">
        {/* Avatar */}
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-bold ${avatar.style}`}>
          {avatar.initials}
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap items-center gap-2">
            {job.source === 'recruiter' && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                Direct role
              </span>
            )}
            {fresh && (
              <span className="rounded-full bg-ember-400/15 px-2 py-0.5 text-xs font-semibold text-ember-700">
                New
              </span>
            )}
            <span className="text-xs text-neutral-400">{formatDate(job.posted_date || job.scraped_at)}</span>
          </div>

          <Link
            href={`/jobs/${job.id}`}
            data-job-id={job.id}
            className="block text-lg font-semibold leading-snug text-neutral-900 transition-colors hover:text-brand-turquoise-700"
          >
            {job.title}
          </Link>
          <p className="mt-0.5 text-sm font-medium text-neutral-600">{job.company}</p>

          {/* Metadata chips */}
          <div className="mt-3 flex flex-wrap gap-2">
            {job.location && <Chip icon={MapPin}>{job.location}</Chip>}
            {(job.remote_type || job.remote_option) && (
              <Chip icon={Globe}>{prettify(job.remote_type || job.remote_option)}</Chip>
            )}
            {job.job_type && <Chip icon={Briefcase}>{prettify(job.job_type)}</Chip>}
            {job.experience_level && <Chip icon={TrendingUp}>{prettify(job.experience_level)}</Chip>}
            {salary && <Chip icon={Banknote}>{salary}</Chip>}
          </div>

          <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-neutral-500">
            {cleanJobDescription(job.description)}
          </p>

          {/* Skills */}
          {skills.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full border border-brand-turquoise-100 bg-brand-turquoise-50 px-2 py-0.5 text-xs font-medium text-brand-turquoise-700"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {applyHref && (
                <a
                  href={applyHref}
                  data-analytics="job_apply_click"
                  data-job-id={job.id}
                  target="_blank"
                rel="noopener noreferrer nofollow"
                onClick={() => toast.success('Create a profile later to track applications and get similar jobs.')}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
              >
                Apply <ArrowRight className="h-3.5 w-3.5" />
              </a>
            )}
            <Link
              href={`/jobs/${job.id}`}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-neutral-200 px-4 py-2 text-sm font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:bg-neutral-50"
            >
              View details
            </Link>
          </div>
        </div>

        {/* Save */}
        <button
          type="button"
          aria-label={saved ? 'Saved' : 'Save job'}
          onClick={() => onSave(job.id)}
          className={`absolute right-4 top-4 inline-flex h-9 w-9 items-center justify-center rounded-lg border transition-colors ${
            saved
              ? 'border-brand-turquoise-200 bg-brand-turquoise-50 text-brand-turquoise-700'
              : 'border-transparent text-neutral-300 hover:border-neutral-200 hover:bg-neutral-50 hover:text-neutral-500'
          }`}
        >
          <Bookmark className={`h-4 w-4 ${saved ? 'fill-current' : ''}`} />
        </button>
      </div>
    </article>
  )
}

const POPULAR_SEARCHES = [
  'Software Engineer',
  'Data Analyst',
  'Customer Support',
  'Sales',
  'Product Manager',
  'Marketing',
]

const TRUST_POINTS = [
  {
    icon: Building2,
    title: 'Real, checkable roles',
    copy: 'Recruiter-posted openings alongside listings curated from trusted job boards.',
  },
  {
    icon: Globe,
    title: 'Remote-friendly',
    copy: 'Filter to remote-only in one tap, or search by the city you actually want.',
  },
  {
    icon: TrendingUp,
    title: 'Your shortlist, free',
    copy: 'Add your CV and we rank every role against your skills — no cost, no spam.',
  },
]

export default function JobsClient() {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const [jobs, setJobs] = useState<Job[]>([])
  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [location, setLocation] = useState('')
  const [appliedLocation, setAppliedLocation] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('all')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set())
  const [showSignupPrompt, setShowSignupPrompt] = useState(false)

  useEffect(() => {
    if (authLoading || isAuthenticated) return

    try {
      if (window.sessionStorage.getItem(SIGNUP_PROMPT_DISMISSED_KEY) === 'true') return
    } catch {
      // Continue if browser storage is unavailable.
    }

    const timer = window.setTimeout(() => setShowSignupPrompt(true), 5000)
    return () => window.clearTimeout(timer)
  }, [authLoading, isAuthenticated])

  const closeSignupPrompt = () => {
    setShowSignupPrompt(false)
    try {
      window.sessionStorage.setItem(SIGNUP_PROMPT_DISMISSED_KEY, 'true')
    } catch {
      // The prompt is still dismissible if browser storage is unavailable.
    }
  }

  useEffect(() => {
    setPage(1)
  }, [appliedQuery, appliedLocation, viewMode, remoteOnly])

  useEffect(() => {
    void loadJobs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, appliedQuery, appliedLocation, viewMode, remoteOnly])

  const loadJobs = async () => {
    try {
      setLoading(true)
      setLoadFailed(false)
      const params: JobSearchParams = { page, page_size: PAGE_SIZE }
      if (appliedQuery.trim()) params.q = appliedQuery.trim()
      if (appliedLocation.trim()) params.location = appliedLocation.trim()
      if (viewMode === 'recruiter') params.source = 'recruiter'
      if (remoteOnly) params.remote_type = 'remote'

      const response = await searchJobs(params)
      setJobs(response.jobs)
      setTotal(response.total)
      setTotalPages(Math.max(1, response.total_pages))
    } catch (error) {
      console.error('Failed to load jobs', error)
      // No toast here: overlapping loads used to stack duplicate toasts over the
      // header. The inline panel below is the single failure surface, and it
      // offers a retry.
      setLoadFailed(true)
      setJobs([])
      setTotal(0)
      setTotalPages(1)
    } finally {
      setLoading(false)
    }
  }

  const hasFilters = useMemo(
    () => appliedQuery.trim() || appliedLocation.trim() || viewMode !== 'all' || remoteOnly,
    [appliedQuery, appliedLocation, viewMode, remoteOnly],
  )

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault()
    setAppliedQuery(query)
    setAppliedLocation(location)
  }

  const runQuickSearch = (term: string) => {
    setQuery(term)
    setAppliedQuery(term)
  }

  const clearFilters = () => {
    setQuery('')
    setLocation('')
    setAppliedQuery('')
    setAppliedLocation('')
    setViewMode('all')
    setRemoteOnly(false)
  }

  const toggleSave = (id: string) => {
    setSavedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
        toast('Sign up free to keep your saved jobs & track applications.', { icon: '🔖' })
      }
      return next
    })
  }

  return (
    <>
      <PostApplyModal
        open={showSignupPrompt}
        onClose={closeSignupPrompt}
        heading="Sign up now for tailored roles"
        description="Create a free profile and get jobs ranked around your experience, skills, and career goals."
        ctaLabel="Sign up for tailored roles"
      />
      <main className="min-h-screen bg-cream-50 text-ink-900">
        {/* ============================================================== */}
        {/* Hero — warm, human, and the search box lives right in it       */}
        {/* ============================================================== */}
        <header className="relative overflow-hidden bg-forest-700 text-cream-100">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-24 -top-40 h-[28rem] w-[28rem] rounded-full bg-ember-400/10 blur-3xl"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -left-32 bottom-0 h-80 w-80 rounded-full bg-brand-turquoise-500/10 blur-3xl"
          />

          <div className="relative mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
            <Link href="/" className="inline-flex items-center gap-2.5 text-lg font-semibold tracking-tight">
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-cream-100">
                <Image src="/logo.png" alt="" width={20} height={20} priority className="object-contain" />
              </span>
              <span>
                Veloxa<span className="text-ember-300">Hire</span>
              </span>
            </Link>
            <div className="flex items-center gap-1 sm:gap-2">
              <Link
                href="/remote-jobs"
                className="hidden px-3 py-2 text-sm text-cream-100/75 transition-colors hover:text-cream-100 md:inline-flex"
              >
                Remote jobs
              </Link>
              <Link
                href="/auth/login"
                className="hidden px-3 py-2 text-sm text-cream-100/75 transition-colors hover:text-cream-100 sm:inline-flex"
              >
                Sign in
              </Link>
              <Link
                href="/auth/signup"
                className="inline-flex items-center gap-1.5 rounded-full bg-cream-100 px-4 py-2 text-sm font-semibold text-ink-900 transition-colors hover:bg-white"
              >
                Get recommendations
              </Link>
            </div>
          </div>

          <section className="relative mx-auto max-w-6xl px-4 pb-12 pt-6 sm:px-6 lg:pb-16">
            <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
              <div>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-cream-100/20 bg-cream-100/10 px-3 py-1 text-xs font-semibold text-ember-300">
                  Free to browse — no account needed
                </span>

                <h1 className="mt-4 font-display text-4xl font-bold leading-[1.08] tracking-tight sm:text-5xl">
                  Find a job that&apos;s{' '}
                  <span className="font-light italic text-ember-300">actually</span> worth
                  applying to.
                </h1>

                <p className="mt-4 max-w-xl text-lg leading-relaxed text-cream-100/75">
                  Search recruiter-posted roles and curated listings from across the web. Create a
                  free profile whenever you want your CV ranked against every one of them.
                </p>

                <form
                  onSubmit={submitSearch}
                  className="mt-7 rounded-2xl border border-cream-100/15 bg-cream-100/[0.07] p-2 sm:flex sm:items-center sm:gap-2"
                >
                  <label className="relative block flex-1">
                    <span className="sr-only">Search by role, company, or keyword</span>
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Job title or company"
                      className="w-full rounded-xl bg-cream-50 py-3 pl-10 pr-3 text-sm text-ink-900 outline-none ring-ember-400/50 placeholder:text-neutral-400 focus:ring-2"
                    />
                  </label>
                  <label className="relative mt-2 block sm:mt-0 sm:w-48">
                    <span className="sr-only">Location</span>
                    <MapPin className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                    <input
                      value={location}
                      onChange={(event) => setLocation(event.target.value)}
                      placeholder="City or “remote”"
                      className="w-full rounded-xl bg-cream-50 py-3 pl-10 pr-3 text-sm text-ink-900 outline-none ring-ember-400/50 placeholder:text-neutral-400 focus:ring-2"
                    />
                  </label>
                  <button
                    type="submit"
                    className="mt-2 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-ember-500 px-6 py-3 text-sm font-semibold text-ink-900 transition-colors hover:bg-ember-400 sm:mt-0 sm:w-auto"
                  >
                    <Search className="h-4 w-4" />
                    Search
                  </button>
                </form>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <span className="text-xs text-cream-100/50">Popular right now:</span>
                  {POPULAR_SEARCHES.map((term) => (
                    <button
                      key={term}
                      type="button"
                      onClick={() => runQuickSearch(term)}
                      className="rounded-full border border-cream-100/15 px-3 py-1 text-xs font-medium text-cream-100/75 transition-colors hover:border-ember-300/50 hover:bg-cream-100/5 hover:text-cream-100"
                    >
                      {term}
                    </button>
                  ))}
                </div>
              </div>

              <div className="relative mx-auto w-full max-w-md lg:max-w-none">
                <div className="overflow-hidden rounded-[1.75rem] border border-cream-100/15 shadow-2xl shadow-ink-900/40">
                  <Image
                    src="/landing/jobseekers-smiling.jpg"
                    alt="Two smiling young professionals holding a laptop in a bright office"
                    width={1600}
                    height={1200}
                    priority
                    sizes="(max-width: 1024px) 100vw, 480px"
                    className="h-full w-full object-cover"
                  />
                </div>

                {!loading && !loadFailed && total > 0 && (
                  <div className="absolute -bottom-5 -left-3 hidden rounded-2xl border border-cream-100/15 bg-ink-800/95 px-4 py-3 shadow-xl backdrop-blur sm:block">
                    <p className="text-[11px] uppercase tracking-wider text-cream-100/50">
                      Live on VeloxaHire
                    </p>
                    <p className="mt-1 text-lg font-semibold leading-none">
                      {total.toLocaleString()}{' '}
                      <span className="text-sm font-medium text-cream-100/70">open roles</span>
                    </p>
                  </div>
                )}

                <div className="absolute -right-3 top-6 hidden items-center gap-2 rounded-full border border-cream-100/15 bg-ink-800/95 px-3 py-2 shadow-xl backdrop-blur sm:flex">
                  <Bell className="h-4 w-4 text-ember-300" />
                  <span className="text-xs font-medium">New roles added daily</span>
                </div>
              </div>
            </div>

            <ul className="mt-14 grid gap-3 sm:grid-cols-3">
              {TRUST_POINTS.map(({ icon: Icon, title, copy }) => (
                <li
                  key={title}
                  className="flex items-start gap-3 rounded-2xl border border-cream-100/10 bg-cream-100/[0.04] px-4 py-3.5"
                >
                  <Icon className="mt-0.5 h-4 w-4 shrink-0 text-ember-300" />
                  <div>
                    <p className="text-sm font-semibold">{title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-cream-100/60">{copy}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </header>

        {/* ============================================================== */}
        {/* Results                                                        */}
        {/* ============================================================== */}
        <section className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
          <div className="flex flex-col gap-4 rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setViewMode('all')}
                className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${viewMode === 'all' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:text-neutral-900'}`}
              >
                All jobs
              </button>
              <button
                type="button"
                onClick={() => setViewMode('recruiter')}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${viewMode === 'recruiter' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:text-neutral-900'}`}
              >
                <Briefcase className="h-3.5 w-3.5" />
                Direct recruiter roles
              </button>
              <button
                type="button"
                onClick={() => setRemoteOnly((value) => !value)}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${remoteOnly ? 'bg-brand-turquoise-600 text-white' : 'bg-neutral-100 text-neutral-600 hover:text-neutral-900'}`}
              >
                <Globe className="h-3.5 w-3.5" />
                Remote
              </button>
              {hasFilters && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium text-neutral-500 transition-colors hover:text-neutral-900"
                >
                  <X className="h-3.5 w-3.5" />
                  Clear
                </button>
              )}
            </div>

            <p className="text-sm text-neutral-500">
              {loading
                ? 'Loading jobs…'
                : loadFailed
                  ? 'Jobs unavailable'
                  : `${total.toLocaleString()} job${total === 1 ? '' : 's'} found`}
              {!loading && !loadFailed && totalPages > 1 ? ` · page ${page} of ${totalPages}` : ''}
            </p>
          </div>

          {appliedQuery.trim() || appliedLocation.trim() ? (
            <p className="mt-4 text-sm text-neutral-500">
              Showing results for{' '}
              <span className="font-semibold text-neutral-800">
                {[appliedQuery.trim(), appliedLocation.trim()].filter(Boolean).join(' · ')}
              </span>
            </p>
          ) : null}

          {loading ? (
            <div className="mt-6 grid gap-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : loadFailed ? (
            <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50/70 p-12 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-amber-100">
                <AlertCircle className="h-5 w-5 text-amber-600" />
              </div>
              <p className="font-semibold text-neutral-900">We couldn&apos;t load jobs just now</p>
              <p className="mx-auto mt-1 max-w-sm text-sm text-neutral-600">
                This is usually temporary. Your search is still here — give it another try.
              </p>
              <button
                type="button"
                onClick={() => void loadJobs()}
                className="mt-5 inline-flex items-center gap-1.5 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
              >
                <RefreshCw className="h-4 w-4" />
                Try again
              </button>
            </div>
          ) : jobs.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-dashed border-neutral-300 bg-white p-12 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-100">
                <Search className="h-5 w-5 text-neutral-400" />
              </div>
              <p className="font-semibold text-neutral-900">No jobs match your search</p>
              <p className="mx-auto mt-1 max-w-sm text-sm text-neutral-500">
                Try a broader title, a different location, or clear your filters to see everything.
              </p>
              {hasFilters && (
                <button
                  onClick={clearFilters}
                  className="mt-5 inline-flex items-center gap-1.5 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
                >
                  Clear filters & browse all
                </button>
              )}
            </div>
          ) : (
            <div className="mt-6 grid gap-3">
              {jobs.map((job) => (
                <JobCard key={job.id} job={job} saved={savedIds.has(job.id)} onSave={toggleSave} />
              ))}
            </div>
          )}

          {!loading && !loadFailed && totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                disabled={page === 1}
                className="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-neutral-500">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                disabled={page === totalPages}
                className="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}

          <aside className="mt-12 overflow-hidden rounded-3xl border border-brand-turquoise-100 bg-gradient-to-br from-brand-turquoise-50 to-cream-100">
            <div className="grid gap-6 p-6 sm:grid-cols-[1fr_auto] sm:items-center sm:p-8">
              <div className="flex items-start gap-4">
                <Image
                  src="/landing/candidate-at-work.jpg"
                  alt=""
                  width={400}
                  height={400}
                  className="hidden h-20 w-20 shrink-0 rounded-2xl object-cover sm:block"
                />
                <div>
                  <p className="font-display text-xl font-semibold text-neutral-900">
                    Stop scrolling. Get a shortlist.
                  </p>
                  <p className="mt-1.5 max-w-md text-sm leading-relaxed text-neutral-600">
                    Add your CV once and VeloxaHire ranks every role against your skills, keeps the
                    ones you save, and tracks what you&apos;ve applied to.
                  </p>
                </div>
              </div>
              <Link
                href="/auth/signup"
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-brand-turquoise-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-turquoise-700"
              >
                Create free profile
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </aside>
        </section>
      </main>
    </>
  )
}
