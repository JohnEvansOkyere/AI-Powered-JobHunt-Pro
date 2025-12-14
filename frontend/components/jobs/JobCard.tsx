'use client'

import { MapPin, Briefcase, Clock, DollarSign, ExternalLink } from 'lucide-react'

export interface Job {
  id: string
  title: string
  company: string
  location: string
  workType: string
  seniority?: string
  salary?: string
  postedDate: string
  description: string
  matchScore?: number
  url: string
}

interface JobCardProps {
  job: Job
  onApply?: (jobId: string) => void
}

export function JobCard({ job, onApply }: JobCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now.getTime() - date.getTime())
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return `${Math.floor(diffDays / 30)} months ago`
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="text-lg font-semibold text-neutral-800">
              {job.title}
            </h3>
            {job.matchScore && (
              <span className="px-2 py-1 text-xs font-medium bg-primary-100 text-primary-700 rounded-full">
                {job.matchScore}% match
              </span>
            )}
          </div>
          <p className="text-neutral-600 font-medium">{job.company}</p>
        </div>
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-600 hover:text-primary-700"
        >
          <ExternalLink className="h-5 w-5" />
        </a>
      </div>

      {/* Job Details */}
      <div className="flex flex-wrap gap-4 mb-4 text-sm text-neutral-600">
        <div className="flex items-center space-x-1">
          <MapPin className="h-4 w-4" />
          <span>{job.location}</span>
        </div>
        <div className="flex items-center space-x-1">
          <Briefcase className="h-4 w-4" />
          <span className="capitalize">{job.workType}</span>
        </div>
        {job.seniority && (
          <div className="flex items-center space-x-1">
            <span className="capitalize">{job.seniority} Level</span>
          </div>
        )}
        {job.salary && (
          <div className="flex items-center space-x-1">
            <DollarSign className="h-4 w-4" />
            <span>{job.salary}</span>
          </div>
        )}
        <div className="flex items-center space-x-1">
          <Clock className="h-4 w-4" />
          <span>{formatDate(job.postedDate)}</span>
        </div>
      </div>

      {/* Description Preview */}
      <p className="text-sm text-neutral-600 mb-4 line-clamp-2">
        {job.description}
      </p>

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-neutral-100">
        <button
          onClick={() => onApply?.(job.id)}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium text-sm"
        >
          Generate Application
        </button>
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          View Job →
        </a>
      </div>
    </div>
  )
}

