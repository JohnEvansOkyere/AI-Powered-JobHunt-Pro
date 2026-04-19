'use client'

import { useState, useEffect, useMemo } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { JobFilters, FilterState } from '@/components/jobs/JobFilters'
import { JobCard, type Job as JobCardJob } from '@/components/jobs/JobCard'
import { searchJobs, Job, JobSearchParams } from '@/lib/api/jobs'
import {
  fetchRecommendations,
  type RecommendationItem,
  type Tier,
} from '@/lib/api/recommendations'
import { saveJob, unsaveJob, getSavedJobs } from '@/lib/api/savedJobs'
import { markJobApplied } from '@/lib/api/applications'
import { Search, Loader, X, ArrowLeft } from 'lucide-react'
import { toast } from 'react-hot-toast'

const TIER_META: Record<Tier, { label: string; description: string; dot: string }> = {
  tier1: {
    label: 'Highly recommended',
    description: 'Strong match on your target title and core skills.',
    dot: 'bg-amber-500',
  },
  tier2: {
    label: 'Likely a fit',
    description: 'Adjacent roles with strong semantic match.',
    dot: 'bg-brand-turquoise-500',
  },
  tier3: {
    label: 'All roles',
    description: 'Everything in your target area, sorted by freshness.',
    dot: 'bg-neutral-400',
  },
}

const EMPTY_FILTERS: FilterState = {
  jobTitle: '',
  location: '',
  workType: [],
  seniority: [],
  salaryRange: 'Any',
  datePosted: 'Any',
}

const PAGE_SIZE = 20

function isValidTier(value: string | null): value is Tier {
  return value === 'tier1' || value === 'tier2' || value === 'tier3'
}

function recToCardJob(rec: RecommendationItem): JobCardJob {
  const j = rec.job
  return {
    id: rec.job_id,
    title: j?.title ?? 'Untitled role',
    company: j?.company ?? 'Unknown company',
    location: j?.location ?? '',
    workType: j?.remote_type ?? j?.job_type ?? '',
    postedDate: j?.posted_date ?? j?.scraped_at ?? new Date().toISOString(),
    description: rec.match_reason ?? '',
    matchScore: Math.round(rec.match_score * 100),
    url: j?.job_link ?? j?.source_url ?? '',
  }
}

function jobToCardJob(job: Job): JobCardJob {
  return {
    id: job.id,
    title: job.title,
    company: job.company,
    location: job.location ?? '',
    workType: job.remote_type ?? job.job_type ?? '',
    seniority: job.experience_level ?? undefined,
    postedDate: job.posted_date ?? job.scraped_at ?? new Date().toISOString(),
    description: (job as any).description ?? '',
    url: job.job_link ?? job.source_url ?? '',
  }
}

export default function JobsPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const tierParam = searchParams.get('tier')
  const activeTier: Tier | null = isValidTier(tierParam) ? tierParam : null

  const [cardJobs, setCardJobs] = useState<JobCardJob[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [appliedSearchQuery, setAppliedSearchQuery] = useState('')
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [savedJobs, setSavedJobs] = useState<Set<string>>(new Set())

  // Cache of all recommendations for the current tier (client-side filter).
  const [tierItems, setTierItems] = useState<RecommendationItem[]>([])

  // Reset paging when tier, query, or filters change.
  useEffect(() => {
    setPage(1)
  }, [activeTier, appliedSearchQuery, filters])

  // Load data whenever the inputs change.
  useEffect(() => {
    loadJobs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTier, page, appliedSearchQuery, filters])

  useEffect(() => {
    loadSavedJobs()
  }, [])

  const loadJobs = async () => {
    try {
      setLoading(true)

      if (activeTier) {
        // Tier mode: fetch once (cached), filter + paginate client-side.
        let items = tierItems
        if (items.length === 0) {
          const res = await fetchRecommendations(activeTier, 1, 100)
          items = res.items
          setTierItems(items)
        }
        const filtered = applyClientFilters(items, appliedSearchQuery, filters)
        setTotal(filtered.length)
        setTotalPages(Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)))
        const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
        setCardJobs(paged.map(recToCardJob))
      } else {
        // Search mode: server-side filtering.
        const params: JobSearchParams = { page, page_size: PAGE_SIZE }
        if (filters.jobTitle) params.q = filters.jobTitle
        else if (appliedSearchQuery) params.q = appliedSearchQuery
        if (filters.location) params.location = filters.location
        if (filters.workType.length > 0) {
          const remoteType = filters.workType[0].toLowerCase()
          if (['remote', 'hybrid', 'onsite'].includes(remoteType)) {
            params.remote_type = remoteType
          }
        }
        if (filters.datePosted !== 'Any') {
          const daysMap: Record<string, number> = {
            'Last 24 hours': 1,
            'Last week': 7,
            'Last month': 30,
            'Last 3 months': 90,
          }
          if (daysMap[filters.datePosted]) {
            params.min_posted_days = daysMap[filters.datePosted]
          }
        }
        const response = await searchJobs(params)
        setCardJobs(response.jobs.map(jobToCardJob))
        setTotal(response.total)
        setTotalPages(response.total_pages)
      }
    } catch (error) {
      console.error('Error loading jobs:', error)
      toast.error('Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }

  // Reset tier cache when the tier itself changes.
  useEffect(() => {
    setTierItems([])
  }, [activeTier])

  const loadSavedJobs = async () => {
    try {
      const savedApplications = await getSavedJobs()
      setSavedJobs(new Set(savedApplications.map((app) => app.job_id)))
    } catch (error) {
      console.error('Error loading saved jobs:', error)
    }
  }

  const handleApply = async (jobId: string) => {
    try {
      await markJobApplied(jobId)
    } catch (error) {
      console.error('Error marking job applied:', error)
    }
  }

  const handleSaveToggle = async (jobId: string) => {
    const isSaved = savedJobs.has(jobId)
    try {
      if (isSaved) {
        await unsaveJob(jobId)
        setSavedJobs((prev) => {
          const next = new Set(prev)
          next.delete(jobId)
          return next
        })
        toast.success('Removed from saved')
      } else {
        await saveJob(jobId)
        setSavedJobs((prev) => new Set(prev).add(jobId))
        toast.success('Saved')
      }
    } catch (error: any) {
      const detail = error?.response?.data?.detail
      if (error?.response?.status === 400 && detail?.includes?.('maximum limit')) {
        toast.error('You have reached the maximum number of saved jobs.')
      } else {
        toast.error(detail || 'Failed to save job')
      }
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setAppliedSearchQuery(searchQuery)
  }

  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters)
  }

  const clearTier = () => {
    router.push('/dashboard/jobs')
  }

  const pageTitle = activeTier ? TIER_META[activeTier].label : 'Jobs'
  const pageDescription = activeTier
    ? TIER_META[activeTier].description
    : 'Browse your matches or search the full index.'

  const hasActiveFilters = useMemo(() => {
    return (
      appliedSearchQuery.trim().length > 0 ||
      filters.jobTitle.trim().length > 0 ||
      filters.location.trim().length > 0 ||
      filters.workType.length > 0 ||
      filters.seniority.length > 0 ||
      filters.datePosted !== 'Any' ||
      filters.salaryRange !== 'Any'
    )
  }, [appliedSearchQuery, filters])

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <header className="mb-5">
            {activeTier && (
              <Link
                href="/dashboard/recommendations"
                className="inline-flex items-center gap-1 text-xs font-medium text-neutral-500 hover:text-neutral-900 mb-2"
              >
                <ArrowLeft className="w-3 h-3" />
                Back to recommendations
              </Link>
            )}
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  {activeTier && (
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${TIER_META[activeTier].dot}`}
                    />
                  )}
                  <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">
                    {pageTitle}
                  </h1>
                  {activeTier && (
                    <button
                      onClick={clearTier}
                      className="inline-flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 bg-neutral-100 hover:bg-neutral-200 rounded-md px-1.5 py-0.5 transition-colors"
                      aria-label="Clear tier filter"
                    >
                      <X className="w-3 h-3" />
                      Clear
                    </button>
                  )}
                </div>
                <p className="text-sm text-neutral-500 mt-0.5">{pageDescription}</p>
              </div>
            </div>
          </header>

          {/* Search */}
          <form onSubmit={handleSearch} className="mb-5">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={
                  activeTier
                    ? 'Search within this tier'
                    : 'Search by title, company, or keyword'
                }
                className="w-full pl-9 pr-3 py-2 bg-white border border-neutral-200 rounded-lg focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-500/20 outline-none text-sm text-neutral-900 transition-colors"
              />
            </div>
          </form>

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Filters sidebar */}
            <div className="lg:col-span-1">
              <div className="sticky top-20">
                <JobFilters onFilterChange={handleFilterChange} />
              </div>
            </div>

            {/* Jobs list */}
            <div className="lg:col-span-3">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-xs text-neutral-500">
                  {loading ? 'Loading…' : `${total} job${total !== 1 ? 's' : ''}`}
                  {totalPages > 1 && ` · page ${page} of ${totalPages}`}
                </p>
                {hasActiveFilters && !loading && (
                  <button
                    onClick={() => {
                      setFilters(EMPTY_FILTERS)
                      setSearchQuery('')
                      setAppliedSearchQuery('')
                    }}
                    className="text-xs font-medium text-neutral-500 hover:text-neutral-900"
                  >
                    Reset filters
                  </button>
                )}
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader className="h-6 w-6 text-neutral-300 animate-spin" />
                </div>
              ) : cardJobs.length === 0 ? (
                <div className="bg-white rounded-xl border border-dashed border-neutral-200 p-10 text-center">
                  <p className="text-sm font-medium text-neutral-800 mb-1">
                    No jobs match your filters
                  </p>
                  <p className="text-sm text-neutral-500">
                    Try adjusting your search or clearing filters.
                  </p>
                </div>
              ) : (
                <>
                  <div className="space-y-3">
                    {cardJobs.map((job) => (
                      <JobCard
                        key={job.id}
                        job={job}
                        onApply={handleApply}
                        onSave={handleSaveToggle}
                        isSaved={savedJobs.has(job.id)}
                      />
                    ))}
                  </div>

                  {totalPages > 1 && (
                    <div className="flex items-center justify-center gap-2 mt-6">
                      <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="inline-flex items-center px-3 py-1.5 bg-white border border-neutral-200 hover:border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Previous
                      </button>
                      <span className="text-xs text-neutral-500 tabular-nums">
                        {page} / {totalPages}
                      </span>
                      <button
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="inline-flex items-center px-3 py-1.5 bg-white border border-neutral-200 hover:border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Next
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

// Client-side filter for tier view. We already fetched up to 100 pre-ranked
// items, so location/search/remote-type filters run cheaply in memory.
function applyClientFilters(
  items: RecommendationItem[],
  query: string,
  filters: FilterState,
): RecommendationItem[] {
  const q = (filters.jobTitle || query || '').trim().toLowerCase()
  const loc = filters.location.trim().toLowerCase()
  const remoteTypes = filters.workType.map((w) => w.toLowerCase())
  const dayCutoff = datePostedCutoff(filters.datePosted)

  return items.filter((rec) => {
    const job = rec.job
    if (!job) return false

    if (q) {
      const haystack = `${job.title ?? ''} ${job.company ?? ''}`.toLowerCase()
      if (!haystack.includes(q)) return false
    }
    if (loc) {
      if (!(job.location ?? '').toLowerCase().includes(loc)) return false
    }
    if (remoteTypes.length > 0) {
      const rt = (job.remote_type ?? '').toLowerCase()
      if (!remoteTypes.includes(rt)) return false
    }
    if (dayCutoff !== null) {
      const ts = job.posted_date ?? job.scraped_at
      if (!ts) return false
      const ageDays = (Date.now() - new Date(ts).getTime()) / 86_400_000
      if (ageDays > dayCutoff) return false
    }
    return true
  })
}

function datePostedCutoff(value: string): number | null {
  switch (value) {
    case 'Last 24 hours':
      return 1
    case 'Last week':
      return 7
    case 'Last month':
      return 30
    case 'Last 3 months':
      return 90
    default:
      return null
  }
}
