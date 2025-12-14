'use client'

import { useState, useEffect } from 'react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { JobFilters, FilterState } from '@/components/jobs/JobFilters'
import { JobCard, Job } from '@/components/jobs/JobCard'
import { Search, Sparkles } from 'lucide-react'

// Mock data - will be replaced with API calls
const mockJobs: Job[] = [
  {
    id: '1',
    title: 'Senior Software Engineer',
    company: 'Tech Corp',
    location: 'San Francisco, CA (Remote)',
    workType: 'Remote',
    seniority: 'Senior',
    salary: '$120k - $180k',
    postedDate: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    description:
      'We are looking for an experienced software engineer to join our team. You will work on building scalable web applications using modern technologies.',
    matchScore: 95,
    url: '#',
  },
  {
    id: '2',
    title: 'Full Stack Developer',
    company: 'StartupXYZ',
    location: 'New York, NY',
    workType: 'Hybrid',
    seniority: 'Mid',
    salary: '$90k - $130k',
    postedDate: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    description:
      'Join our fast-growing startup as a full stack developer. Work with React, Node.js, and modern cloud infrastructure.',
    matchScore: 88,
    url: '#',
  },
  {
    id: '3',
    title: 'Frontend Engineer',
    company: 'Design Co',
    location: 'Austin, TX (Remote)',
    workType: 'Remote',
    seniority: 'Mid',
    salary: '$85k - $120k',
    postedDate: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    description:
      'We need a talented frontend engineer to help us build beautiful user interfaces. Experience with React and TypeScript required.',
    matchScore: 92,
    url: '#',
  },
]

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>(mockJobs)
  const [filteredJobs, setFilteredJobs] = useState<Job[]>(mockJobs)
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<FilterState>({
    jobTitle: '',
    location: '',
    workType: [],
    seniority: [],
    salaryRange: 'Any',
    datePosted: 'Any',
  })
  const [loading, setLoading] = useState(false)

  // Filter jobs based on search and filters
  useEffect(() => {
    let filtered = [...jobs]

    // Search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (job) =>
          job.title.toLowerCase().includes(query) ||
          job.company.toLowerCase().includes(query) ||
          job.description.toLowerCase().includes(query)
      )
    }

    // Job title filter
    if (filters.jobTitle) {
      filtered = filtered.filter((job) =>
        job.title.toLowerCase().includes(filters.jobTitle.toLowerCase())
      )
    }

    // Location filter
    if (filters.location) {
      filtered = filtered.filter((job) =>
        job.location.toLowerCase().includes(filters.location.toLowerCase())
      )
    }

    // Work type filter
    if (filters.workType.length > 0) {
      filtered = filtered.filter((job) =>
        filters.workType.includes(job.workType)
      )
    }

    // Seniority filter
    if (filters.seniority.length > 0) {
      filtered = filtered.filter(
        (job) => job.seniority && filters.seniority.includes(job.seniority)
      )
    }

    // Sort by match score (highest first)
    filtered.sort((a, b) => (b.matchScore || 0) - (a.matchScore || 0))

    setFilteredJobs(filtered)
  }, [jobs, searchQuery, filters])

  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters)
  }

  const handleApply = (jobId: string) => {
    // TODO: Navigate to application generation page
    console.log('Generate application for job:', jobId)
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
          <div className="mb-6">
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
          </div>

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
                  {filteredJobs.length} job{filteredJobs.length !== 1 ? 's' : ''}{' '}
                  found
                </p>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-700"></div>
                </div>
              ) : filteredJobs.length === 0 ? (
                <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-12 text-center">
                  <p className="text-neutral-600 mb-2">No jobs found</p>
                  <p className="text-sm text-neutral-500">
                    Try adjusting your filters or search query
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredJobs.map((job) => (
                    <JobCard
                      key={job.id}
                      job={job}
                      onApply={handleApply}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

