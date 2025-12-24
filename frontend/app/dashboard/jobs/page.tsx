'use client'

import { useState, useEffect } from 'react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { JobFilters, FilterState } from '@/components/jobs/JobFilters'
import { JobCard } from '@/components/jobs/JobCard'
import { searchJobs, Job, JobSearchParams } from '@/lib/api/jobs'
import { Search, Sparkles, Loader } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function JobsPage() {
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

  // Load jobs from API
  useEffect(() => {
    loadJobs()
  }, [page, searchQuery, filters])

  const loadJobs = async () => {
    try {
      setLoading(true)
      
      const params: JobSearchParams = {
        page,
        page_size: 20,
        matched: true, // Get matched jobs with scores
      }
      
      // Add search query
      if (searchQuery) {
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

  const handleApply = (jobId: string) => {
    // TODO: Navigate to application generation page
    console.log('Generate application for job:', jobId)
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
              <Sparkles className="h-6 w-6 text-primary-600" />
              <h1 className="text-3xl font-bold text-neutral-800">
                Job Recommendations
              </h1>
            </div>
            <p className="text-neutral-600">
              AI-powered job matches based on your profile
            </p>
          </div>

          {/* Search Bar */}
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

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Filters Sidebar */}
            <div className="lg:col-span-1">
              <div className="sticky top-24">
                <JobFilters onFilterChange={handleFilterChange} />
              </div>
            </div>

            {/* Jobs List */}
            <div className="lg:col-span-3">
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
                          matchScore: job.match_score || 0,
                          url: job.job_link,
                        }}
                        onApply={handleApply}
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

