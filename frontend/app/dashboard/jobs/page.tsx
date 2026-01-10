'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { JobFilters, FilterState } from '@/components/jobs/JobFilters'
import { JobCard } from '@/components/jobs/JobCard'
import { searchJobs, getRecommendations, Job, JobSearchParams } from '@/lib/api/jobs'
import { saveJob, unsaveJob, getSavedJobs } from '@/lib/api/savedJobs'
import { Search, Sparkles, Loader, Briefcase } from 'lucide-react'
import { toast } from 'react-hot-toast'

type TabType = 'recommendations' | 'all-jobs'

export default function JobsPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<TabType>('recommendations')
  const [jobs, setJobs] = useState<Job[]>([])
  const [filteredJobs, setFilteredJobs] = useState<Job[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<FilterState>({
    jobTitle: '',
    location: '',
    workType: [],
    seniority: [],
    salaryRange: 'Any',
    datePosted: 'Any',
  })
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [savedJobs, setSavedJobs] = useState<Set<string>>(new Set())

  // Load jobs from API when tab, page, or filters change
  useEffect(() => {
    loadJobs()
  }, [activeTab, page, searchQuery, filters])

  // Reset to page 1 when changing tabs
  useEffect(() => {
    setPage(1)
  }, [activeTab])

  // Load saved jobs on mount
  useEffect(() => {
    loadSavedJobs()
  }, [])

  const loadJobs = async () => {
    try {
      setLoading(true)

      if (activeTab === 'recommendations') {
        // Recommendations tab: Fetch pre-computed recommendations (instant!)
        const response = await getRecommendations(page, 20)
        setJobs(response.jobs)
        setFilteredJobs(response.jobs)
        setTotal(response.total)
        setTotalPages(response.total_pages)
      } else {
        // All Jobs tab: Use filters for direct search
        const params: JobSearchParams = {
          page,
          page_size: 20,
        }

        // Add search query (job title from filter or search box)
        if (filters.jobTitle) {
          params.q = filters.jobTitle
        } else if (searchQuery) {
          params.q = searchQuery
        }

        // Add filters
        if (filters.location) {
          params.location = filters.location
        }

        if (filters.workType.length > 0) {
          // Map workType to remote_type
          const remoteType = filters.workType[0].toLowerCase()
          if (['remote', 'hybrid', 'onsite'].includes(remoteType)) {
            params.remote_type = remoteType
          }
        }

        if (filters.datePosted !== 'Any') {
          // Map datePosted to min_posted_days
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
        setJobs(response.jobs)
        setFilteredJobs(response.jobs)
        setTotal(response.total)
        setTotalPages(response.total_pages)
      }
    } catch (error: any) {
      console.error('Error loading jobs:', error)
      toast.error('Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters)
    setPage(1) // Reset to first page when filters change
  }

  const loadSavedJobs = async () => {
    try {
      const savedApplications = await getSavedJobs()
      const jobIds = new Set(savedApplications.map(app => app.job_id))
      setSavedJobs(jobIds)
    } catch (error) {
      console.error('Error loading saved jobs:', error)
    }
  }

  const handleApply = (jobId: string) => {
    // Navigate to application generation page
    router.push(`/dashboard/applications/generate/${jobId}`)
  }

  const handleSaveToggle = async (jobId: string) => {
    const isSaved = savedJobs.has(jobId)

    try {
      if (isSaved) {
        await unsaveJob(jobId)
        setSavedJobs(prev => {
          const next = new Set(prev)
          next.delete(jobId)
          return next
        })
        toast.success('Job removed from saved')
      } else {
        await saveJob(jobId)
        setSavedJobs(prev => new Set(prev).add(jobId))
        toast.success('Job saved to Applications')
      }
    } catch (error: any) {
      if (error.response?.status === 400 && error.response?.data?.detail?.includes('maximum limit')) {
        toast.error('Maximum 10 saved jobs. Remove some first.')
      } else {
        toast.error(error.response?.data?.detail || 'Failed to save job')
      }
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadJobs()
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-2">
              <Briefcase className="h-6 w-6 text-primary-600" />
              <h1 className="text-3xl font-bold text-neutral-800">
                Jobs
              </h1>
            </div>
            <p className="text-neutral-600">
              Find jobs that match your profile or browse all available positions
            </p>
          </div>

          {/* Tabs */}
          <div className="mb-6">
            <div className="border-b border-neutral-200">
              <nav className="flex space-x-8">
                <button
                  onClick={() => setActiveTab('recommendations')}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${activeTab === 'recommendations'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                    }
                  `}
                >
                  <div className="flex items-center space-x-2">
                    <Sparkles className="h-4 w-4" />
                    <span>Recommended for You</span>
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('all-jobs')}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${activeTab === 'all-jobs'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                    }
                  `}
                >
                  <div className="flex items-center space-x-2">
                    <Search className="h-4 w-4" />
                    <span>All Jobs</span>
                  </div>
                </button>
              </nav>
            </div>
          </div>

          {/* Search Bar - Only show in "All Jobs" tab */}
          {activeTab === 'all-jobs' && (
            <form onSubmit={handleSearch} className="mb-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-neutral-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search jobs by title, company, or keywords..."
                  className="w-full pl-10 pr-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </form>
          )}

          {/* Info banner for Recommendations tab */}
          {activeTab === 'recommendations' && (
            <div className="mb-6 bg-primary-50 border border-primary-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <Sparkles className="h-5 w-5 text-primary-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-medium text-primary-900 mb-1">
                    AI-Powered Job Matching
                  </h3>
                  <p className="text-sm text-primary-700">
                    These jobs are personalized recommendations based on your profile, skills, experience, and preferences using OpenAI embeddings.
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Filters Sidebar - Only show in "All Jobs" tab */}
            {activeTab === 'all-jobs' && (
              <div className="lg:col-span-1">
                <div className="sticky top-24">
                  <JobFilters onFilterChange={handleFilterChange} />
                </div>
              </div>
            )}

            {/* Jobs List */}
            <div className={activeTab === 'all-jobs' ? 'lg:col-span-3' : 'lg:col-span-4'}>
              <div className="mb-4 flex items-center justify-between">
                <p className="text-sm text-neutral-600">
                  {total} job{total !== 1 ? 's' : ''} found
                  {totalPages > 1 && ` (Page ${page} of ${totalPages})`}
                </p>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader className="h-8 w-8 text-primary-600 animate-spin" />
                </div>
              ) : filteredJobs.length === 0 ? (
                <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-12 text-center">
                  <p className="text-neutral-600 mb-2">No jobs found</p>
                  <p className="text-sm text-neutral-500">
                    Try adjusting your filters or search query
                  </p>
                </div>
              ) : (
                <>
                  <div className="space-y-4">
                    {filteredJobs.map((job) => (
                      <JobCard
                        key={job.id}
                        job={{
                          id: job.id,
                          title: job.title,
                          company: job.company,
                          location: job.location || '',
                          workType: job.remote_type || 'Onsite',
                          seniority: 'Mid', // TODO: Extract from description
                          salary: job.salary_range || 'Not specified',
                          postedDate: job.posted_date || job.scraped_at,
                          description: job.description,
                          // Show match score only in recommendations tab
                          matchScore: activeTab === 'recommendations' ? job.match_score : undefined,
                          url: job.job_link,
                        }}
                        onApply={handleApply}
                        onSave={handleSaveToggle}
                        isSaved={savedJobs.has(job.id)}
                      />
                    ))}
                  </div>
                  
                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="mt-6 flex items-center justify-center space-x-2">
                      <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="px-4 py-2 border border-neutral-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-neutral-50"
                      >
                        Previous
                      </button>
                      <span className="px-4 py-2 text-sm text-neutral-600">
                        Page {page} of {totalPages}
                      </span>
                      <button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="px-4 py-2 border border-neutral-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-neutral-50"
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

