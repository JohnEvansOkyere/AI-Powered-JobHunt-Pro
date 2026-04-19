'use client'

import {
  MapPin,
  Briefcase,
  Clock,
  DollarSign,
  ExternalLink,
  Bookmark,
  BookmarkCheck,
} from 'lucide-react'

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
  onSave?: (jobId: string) => void
  isSaved?: boolean
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  const diffDays = Math.ceil(
    Math.abs(Date.now() - date.getTime()) / (1000 * 60 * 60 * 24),
  )
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
  return `${Math.floor(diffDays / 30)}mo ago`
}

export function JobCard({ job, onApply, onSave, isSaved = false }: JobCardProps) {
  const hasExternalLink = Boolean(job.url)

  return (
    <article className="bg-white rounded-xl border border-neutral-200 hover:border-neutral-300 transition-colors p-5">
      {/* Header */}
      <header className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            {job.matchScore !== undefined && (
              <span className="inline-flex items-center text-[11px] font-medium bg-brand-turquoise-50 text-brand-turquoise-700 border border-brand-turquoise-100 rounded-md px-1.5 py-0.5">
                {job.matchScore}% match
              </span>
            )}
          </div>
          <h3 className="text-base font-semibold text-neutral-900 leading-snug">
            {job.title}
          </h3>
          <p className="text-sm text-neutral-500 mt-0.5">{job.company}</p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onSave?.(job.id)
          }}
          aria-label={isSaved ? 'Remove from saved' : 'Save for later'}
          className={`p-1.5 -m-1 rounded-md transition-colors flex-shrink-0 ${
            isSaved
              ? 'text-brand-turquoise-600'
              : 'text-neutral-300 hover:text-neutral-600 hover:bg-neutral-50'
          }`}
        >
          {isSaved ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
        </button>
      </header>

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500 mb-3">
        {job.location && (
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {job.location}
          </span>
        )}
        {job.workType && (
          <span className="inline-flex items-center gap-1 capitalize">
            <Briefcase className="h-3 w-3" />
            {job.workType}
          </span>
        )}
        {job.seniority && <span className="capitalize">{job.seniority}</span>}
        {job.salary && (
          <span className="inline-flex items-center gap-1">
            <DollarSign className="h-3 w-3" />
            {job.salary}
          </span>
        )}
        <span className="inline-flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatDate(job.postedDate)}
        </span>
      </div>

      {/* Description preview */}
      {job.description && (
        <p className="text-sm text-neutral-600 leading-relaxed mb-4 line-clamp-2">
          {job.description}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {hasExternalLink ? (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer nofollow"
            onClick={() => onApply?.(job.id)}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-brand-turquoise-600 hover:bg-brand-turquoise-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Apply
          </a>
        ) : (
          <button
            onClick={() => onApply?.(job.id)}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-sm font-medium transition-colors"
          >
            View details
          </button>
        )}
      </div>
    </article>
  )
}
