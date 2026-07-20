'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  ArrowRight,
  Bell,
  Bookmark,
  Briefcase,
  Banknote,
  Filter,
  Globe,
  MapPin,
  Search,
  Sparkles,
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
                <Sparkles className="h-3 w-3" /> Direct role
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
  const [filtersOpen, setFiltersOpen] = useState(false)
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
      toast.error('Could not load jobs right now')
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
    setFiltersOpen(false)
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
      <header className="border-b border-ink-900/10 bg-forest-700 text-cream-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between gap-4">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            Veloxa<span className="text-ember-300">Hire</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link href="/auth/login" className="hidden sm:inline-flex px-3 py-2 text-sm text-cream-100/75 hover:text-cream-100">
              Sign in
            </Link>
            <Link href="/auth/signup" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-cream-100 text-ink-900 text-sm font-semibold hover:bg-cream-50">
              Get recommendations
              <Sparkles className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-10 pb-12">
          <p className="text-sm font-medium text-ember-300 mb-3">Browse first. Personalize when ready.</p>
          <div className="grid lg:grid-cols-[1fr_340px] gap-8 items-end">
            <div>
              <h1 className="font-display text-4xl sm:text-5xl font-bold tracking-tight leading-tight">
                Find jobs worth applying to.
              </h1>
              <p className="mt-4 text-cream-100/75 text-lg max-w-2xl leading-relaxed">
                Search recruiter-posted roles and curated listings before creating an account. Sign up when you want AI recommendations, saved jobs, and application tracking.
              </p>
              <Link href="/remote-jobs" className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-ember-300 hover:text-cream-100">
                Explore remote jobs
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="rounded-2xl border border-cream-100/15 bg-cream-100/10 p-4">
              <div className="flex items-start gap-3">
                <Bell className="w-5 h-5 text-ember-300 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold">Want the shortlist?</p>
                  <p className="mt-1 text-sm text-cream-100/70">
                    Create a free profile and VeloxaHire will rank the roles that fit your CV.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </header>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <form onSubmit={submitSearch} className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col lg:flex-row gap-3">
            <label className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search by role, company, or keyword"
                className="w-full pl-9 pr-3 py-3 rounded-xl border border-neutral-200 bg-neutral-50 text-sm outline-none focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-500/20"
              />
            </label>
            <label className="relative lg:w-64">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
              <input
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                placeholder="Location"
                className="w-full pl-9 pr-3 py-3 rounded-xl border border-neutral-200 bg-neutral-50 text-sm outline-none focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-500/20"
              />
            </label>
            <button
              type="button"
              onClick={() => setFiltersOpen((value) => !value)}
              className="lg:hidden inline-flex items-center justify-center gap-2 rounded-xl border border-neutral-200 px-4 py-3 text-sm font-semibold text-neutral-700"
            >
              <Filter className="h-4 w-4" />
              Filters
            </button>
            <button type="submit" className="rounded-xl bg-brand-turquoise-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-turquoise-700">
              Search jobs
            </button>
          </div>

          <div className={`${filtersOpen ? 'flex' : 'hidden'} lg:flex mt-4 flex-wrap items-center gap-2`}>
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
              <Sparkles className="h-3.5 w-3.5" />
              Direct recruiter roles
            </button>
            <span className="mx-1 hidden h-5 w-px bg-neutral-200 sm:block" />
            <button
              type="button"
              onClick={() => setRemoteOnly((v) => !v)}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${remoteOnly ? 'bg-brand-turquoise-600 text-white' : 'bg-neutral-100 text-neutral-600 hover:text-neutral-900'}`}
            >
              <Globe className="h-3.5 w-3.5" />
              Remote
            </button>
            {hasFilters && (
              <button type="button" onClick={clearFilters} className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium text-neutral-500 hover:text-neutral-900">
                <X className="h-3.5 w-3.5" />
                Clear
              </button>
            )}
          </div>
        </form>

        <div className="mt-5 flex items-center justify-between gap-3">
          <p className="text-sm text-neutral-500">
            {loading ? 'Loading jobs…' : `${total.toLocaleString()} job${total === 1 ? '' : 's'} found`}
            {!loading && totalPages > 1 ? ` · page ${page} of ${totalPages}` : ''}
          </p>
          <Link href="/auth/signup" className="hidden sm:inline-flex items-center gap-1.5 text-sm font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800">
            Get AI recommendations
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {loading ? (
          <div className="mt-6 grid gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
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
                className="mt-5 inline-flex items-center gap-1.5 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
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

        {!loading && totalPages > 1 && (
          <div className="mt-8 flex items-center justify-center gap-2">
            <button
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={page === 1}
              className="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-neutral-500">{page} / {totalPages}</span>
            <button
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              disabled={page === totalPages}
              className="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}

        <aside className="mt-10 rounded-2xl border border-brand-turquoise-100 bg-brand-turquoise-50 p-5 sm:flex sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <Bookmark className="mt-0.5 h-5 w-5 text-brand-turquoise-700" />
            <div>
              <p className="font-semibold text-neutral-900">Want jobs ranked for your CV?</p>
              <p className="mt-1 text-sm text-neutral-600">Create a profile to save roles, track applications, and get a personalized shortlist.</p>
            </div>
          </div>
          <Link href="/auth/signup" className="mt-4 inline-flex items-center justify-center rounded-xl bg-brand-turquoise-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-turquoise-700 sm:mt-0">
            Create free profile
          </Link>
        </aside>
      </section>
      </main>
    </>
  )
}
