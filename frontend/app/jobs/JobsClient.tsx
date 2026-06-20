'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowRight, Bell, Bookmark, Briefcase, Filter, Loader, Search, Sparkles, X } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { searchJobs, type Job, type JobSearchParams } from '@/lib/api/jobs'

const PAGE_SIZE = 20

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

function jobApplyHref(job: Job) {
  return job.job_link || job.source_url || ''
}

export default function JobsClient() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [location, setLocation] = useState('')
  const [appliedLocation, setAppliedLocation] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('all')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [filtersOpen, setFiltersOpen] = useState(false)

  useEffect(() => {
    setPage(1)
  }, [appliedQuery, appliedLocation, viewMode])

  useEffect(() => {
    void loadJobs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, appliedQuery, appliedLocation, viewMode])

  const loadJobs = async () => {
    try {
      setLoading(true)
      const params: JobSearchParams = { page, page_size: PAGE_SIZE }
      if (appliedQuery.trim()) params.q = appliedQuery.trim()
      if (appliedLocation.trim()) params.location = appliedLocation.trim()
      if (viewMode === 'recruiter') params.source = 'recruiter'

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
    () => appliedQuery.trim() || appliedLocation.trim() || viewMode !== 'all',
    [appliedQuery, appliedLocation, viewMode],
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
  }

  return (
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
              <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
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
              className={`rounded-full px-3 py-1.5 text-sm font-medium ${viewMode === 'all' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:text-neutral-900'}`}
            >
              All jobs
            </button>
            <button
              type="button"
              onClick={() => setViewMode('recruiter')}
              className={`rounded-full px-3 py-1.5 text-sm font-medium ${viewMode === 'recruiter' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:text-neutral-900'}`}
            >
              Direct recruiter roles
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
            {loading ? 'Loading jobs...' : `${total} job${total === 1 ? '' : 's'} found`}
            {!loading && totalPages > 1 ? ` · page ${page} of ${totalPages}` : ''}
          </p>
          <Link href="/auth/signup" className="hidden sm:inline-flex items-center gap-1.5 text-sm font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800">
            Get AI recommendations
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader className="h-7 w-7 animate-spin text-neutral-300" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-dashed border-neutral-200 bg-white p-10 text-center">
            <p className="font-semibold text-neutral-900">No jobs match your search</p>
            <p className="mt-1 text-sm text-neutral-500">Try a broader title or clear your filters.</p>
          </div>
        ) : (
          <div className="mt-6 grid gap-3">
            {jobs.map((job) => (
              <article key={job.id} className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition hover:border-brand-turquoise-200 hover:shadow-md">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      {job.source === 'recruiter' && (
                        <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                          Direct role
                        </span>
                      )}
                      <span className="text-xs text-neutral-400">{formatDate(job.posted_date || job.scraped_at)}</span>
                    </div>
                    <Link href={`/jobs/${job.id}`} className="text-lg font-semibold text-neutral-900 hover:text-brand-turquoise-700">
                      {job.title}
                    </Link>
                    <p className="mt-1 text-sm text-neutral-500">
                      {job.company}{job.location ? ` · ${job.location}` : ''}
                    </p>
                    <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-neutral-600">
                      {job.description}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2 sm:flex-col">
                    <Link href={`/jobs/${job.id}`} className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-neutral-200 px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-300">
                      View details
                    </Link>
                    {jobApplyHref(job) && (
                      <a
                        href={jobApplyHref(job)}
                        target="_blank"
                        rel="noopener noreferrer nofollow"
                        onClick={() => toast.success('Create a profile later to track applications and get similar jobs.')}
                        className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
                      >
                        Apply
                        <ArrowRight className="h-3.5 w-3.5" />
                      </a>
                    )}
                  </div>
                </div>
              </article>
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
  )
}
