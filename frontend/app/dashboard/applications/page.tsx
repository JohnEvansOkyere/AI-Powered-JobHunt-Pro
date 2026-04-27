'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  Bookmark,
  CheckCircle,
  Clock,
  ExternalLink,
  Inbox,
  Trash2,
} from 'lucide-react'
import { toast } from 'react-hot-toast'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { useAuth } from '@/hooks/useAuth'
import {
  listApplications,
  markJobApplied,
  type ApplicationStatus,
  type ApplicationWithJob,
} from '@/lib/api/applications'
import { Application as SavedApplication, getSavedJobs, unsaveJob } from '@/lib/api/savedJobs'

type TabType = 'saved' | 'applied' | 'archive'

const APPLIED_STATUSES: ApplicationStatus[] = ['applied', 'interviewing', 'offer']
const ARCHIVE_STATUSES: ApplicationStatus[] = ['dismissed', 'hidden', 'rejected']

const STATUS_STYLES: Record<ApplicationStatus, string> = {
  saved: 'bg-neutral-100 text-neutral-700',
  applied: 'bg-brand-turquoise-50 text-brand-turquoise-700',
  interviewing: 'bg-indigo-50 text-indigo-700',
  offer: 'bg-emerald-50 text-emerald-700',
  rejected: 'bg-rose-50 text-rose-700',
  dismissed: 'bg-neutral-100 text-neutral-500',
  hidden: 'bg-neutral-100 text-neutral-500',
}

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: 'Saved',
  applied: 'Applied',
  interviewing: 'Interviewing',
  offer: 'Offer',
  rejected: 'Rejected',
  dismissed: 'Dismissed',
  hidden: 'Hidden',
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function daysUntil(expires?: string | null) {
  if (!expires) return null
  const diff = new Date(expires).getTime() - Date.now()
  return Math.max(0, Math.ceil(diff / 86_400_000))
}

export default function ApplicationsPage() {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('saved')
  const [applications, setApplications] = useState<ApplicationWithJob[]>([])
  const [savedJobs, setSavedJobs] = useState<SavedApplication[]>([])
  const [loadingApps, setLoadingApps] = useState(true)
  const [loadingSaved, setLoadingSaved] = useState(true)

  useEffect(() => {
    if (authLoading || !isAuthenticated) {
      setLoadingApps(false)
      return
    }

    ;(async () => {
      try {
        setLoadingApps(true)
        setApplications(await listApplications())
      } catch (e) {
        console.error(e)
        toast.error('Failed to load applications')
      } finally {
        setLoadingApps(false)
      }
    })()
  }, [authLoading, isAuthenticated])

  useEffect(() => {
    if (authLoading || !isAuthenticated || activeTab !== 'saved') return
    ;(async () => {
      try {
        setLoadingSaved(true)
        setSavedJobs(await getSavedJobs())
      } catch (e) {
        console.error(e)
        toast.error('Failed to load saved jobs')
      } finally {
        setLoadingSaved(false)
      }
    })()
  }, [activeTab, authLoading, isAuthenticated])

  const applied = useMemo(
    () => applications.filter((a) => APPLIED_STATUSES.includes(a.status)),
    [applications],
  )
  const archived = useMemo(
    () => applications.filter((a) => ARCHIVE_STATUSES.includes(a.status)),
    [applications],
  )

  const handleUnsave = async (jobId: string) => {
    try {
      await unsaveJob(jobId)
      setSavedJobs((prev) => prev.filter((a) => a.job_id !== jobId))
      toast.success('Removed from saved')
    } catch (e) {
      console.error(e)
      toast.error('Failed to remove')
    }
  }

  const handleMarkApplied = async (app: SavedApplication) => {
    try {
      const updated = await markJobApplied(app.job_id)
      setSavedJobs((prev) => prev.filter((a) => a.job_id !== app.job_id))
      setApplications((prev) => [
        {
          ...updated,
          job: app.job ?? null,
        } as ApplicationWithJob,
        ...prev.filter((a) => a.job_id !== app.job_id),
      ])
      toast.success(`Marked "${app.job?.title ?? 'job'}" as applied`)
    } catch (e) {
      console.error(e)
      toast.error('Could not update status')
    }
  }

  const tabs: { id: TabType; label: string; count: number; icon: typeof Bookmark }[] = [
    { id: 'saved', label: 'Saved', count: savedJobs.length, icon: Bookmark },
    { id: 'applied', label: 'Applied', count: applied.length, icon: CheckCircle },
    { id: 'archive', label: 'Archive', count: archived.length, icon: Inbox },
  ]

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-6xl mx-auto space-y-6">
          <header className="space-y-1">
            <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">
              Applications
            </h1>
            <p className="text-sm text-neutral-500 max-w-2xl">
              Save interesting roles, mark the ones you applied to, and archive the rest.
            </p>
          </header>

          <nav className="inline-flex bg-neutral-100 rounded-lg p-1 gap-1">
            {tabs.map(({ id, label, count, icon: Icon }) => {
              const active = activeTab === id
              return (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? 'bg-white text-neutral-900 shadow-sm'
                      : 'text-neutral-500 hover:text-neutral-700'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{label}</span>
                  <span
                    className={`text-xs rounded-full px-1.5 py-0 tabular-nums ${
                      active ? 'bg-neutral-100 text-neutral-700' : 'bg-white text-neutral-500'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              )
            })}
          </nav>

          {activeTab === 'saved' && (
            <section>
              {loadingSaved ? (
                <LoadingCard label="Loading saved jobs…" />
              ) : savedJobs.length === 0 ? (
                <EmptyCard
                  icon={Bookmark}
                  title="No saved jobs yet"
                  description="When you find a role that interests you, tap the bookmark to keep it here."
                  action={
                    <Link
                      href="/dashboard/recommendations"
                      className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-brand-turquoise-600 hover:bg-brand-turquoise-700 text-white font-medium text-sm transition-colors"
                    >
                      Browse recommendations
                    </Link>
                  }
                />
              ) : (
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-5">
                  {savedJobs.map((app, i) => {
                    const daysLeft = daysUntil(app.expires_at ?? null)
                    const job = app.job
                    return (
                      <motion.li
                        key={app.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                        className="group bg-white rounded-xl border border-neutral-200 hover:border-neutral-300 p-5 transition-colors flex flex-col"
                      >
                        <header className="flex items-start justify-between gap-3 mb-3">
                          <div className="min-w-0">
                            <h3 className="text-base font-semibold text-neutral-900 truncate">
                              {job?.title ?? 'Saved job'}
                            </h3>
                            <p className="text-sm text-neutral-500 truncate">
                              {job?.company ?? '—'}
                            </p>
                          </div>
                          <span className="shrink-0 text-xs font-medium rounded-md bg-neutral-50 text-neutral-600 border border-neutral-200 px-1.5 py-0.5">
                            Saved
                          </span>
                        </header>

                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-4 text-xs text-neutral-500">
                          {job?.location && <span>{job.location}</span>}
                          {job?.remote_type && <span className="capitalize">{job.remote_type}</span>}
                          {job?.job_type && <span className="capitalize">{job.job_type}</span>}
                          {daysLeft !== null && daysLeft <= 3 && (
                            <span className="text-brand-orange-700 font-medium">
                              Expires in {daysLeft}d
                            </span>
                          )}
                        </div>

                        <div className="mt-auto flex flex-wrap items-center gap-2">
                          {job?.job_link && (
                            <a
                              href={job.job_link}
                              target="_blank"
                              rel="noopener noreferrer nofollow"
                              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-brand-turquoise-600 hover:bg-brand-turquoise-700 text-white font-medium text-xs transition-colors"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                              Apply
                            </a>
                          )}
                          <button
                            onClick={() => handleMarkApplied(app)}
                            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white font-medium text-xs transition-colors"
                          >
                            <CheckCircle className="w-3.5 h-3.5" />
                            Mark applied
                          </button>
                          <button
                            onClick={() => handleUnsave(app.job_id)}
                            className="inline-flex items-center gap-1.5 px-2 py-2 rounded-lg text-neutral-500 hover:text-rose-600 hover:bg-rose-50 text-xs font-medium transition-colors ml-auto"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Remove
                          </button>
                        </div>
                      </motion.li>
                    )
                  })}
                </ul>
              )}
            </section>
          )}

          {activeTab === 'applied' && (
            <ApplicationList
              loading={loadingApps}
              items={applied}
              emptyTitle="Nothing applied to yet"
              emptyDescription="Once you click Apply on a recommended role and mark it as applied, it shows up here."
            />
          )}

          {activeTab === 'archive' && (
            <ApplicationList
              loading={loadingApps}
              items={archived}
              emptyTitle="Archive is empty"
              emptyDescription="Dismissed, hidden and rejected roles end up here so your main view stays focused."
            />
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

function ApplicationList({
  loading,
  items,
  emptyTitle,
  emptyDescription,
}: {
  loading: boolean
  items: ApplicationWithJob[]
  emptyTitle: string
  emptyDescription: string
}) {
  if (loading) return <LoadingCard label="Loading applications…" />
  if (items.length === 0) {
    return <EmptyCard icon={Inbox} title={emptyTitle} description={emptyDescription} />
  }
  return (
    <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-5">
      {items.map((app, i) => (
        <motion.li
          key={app.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.03 }}
          className="bg-white rounded-xl border border-neutral-200 p-5"
        >
          <header className="flex items-start justify-between gap-3 mb-3">
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-neutral-900 truncate">
                {app.job?.title ?? 'Application'}
              </h3>
              <p className="text-sm text-neutral-500 truncate">{app.job?.company ?? '—'}</p>
            </div>
            <span
              className={`shrink-0 text-xs font-medium rounded-md px-1.5 py-0.5 ${STATUS_STYLES[app.status]}`}
            >
              {STATUS_LABELS[app.status]}
            </span>
          </header>
          <div className="text-xs text-neutral-500 flex flex-wrap gap-x-3 gap-y-1 mb-3">
            <span>Created {formatDate(app.created_at)}</span>
            <span>Updated {formatDate(app.updated_at)}</span>
          </div>
          <div className="flex gap-2">
            {app.job?.job_link && (
              <a
                href={app.job.job_link}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white font-medium text-xs transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View listing
              </a>
            )}
          </div>
        </motion.li>
      ))}
    </ul>
  )
}

function LoadingCard({ label }: { label: string }) {
  return (
    <div className="bg-white rounded-xl border border-neutral-200 p-10 text-center">
      <Clock className="h-6 w-6 text-neutral-300 mx-auto mb-3 animate-spin" />
      <p className="text-sm text-neutral-500">{label}</p>
    </div>
  )
}

function EmptyCard({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: typeof Bookmark
  title: string
  description: string
  action?: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-dashed border-neutral-200 p-10 text-center">
      <div className="w-10 h-10 mx-auto mb-3 rounded-lg bg-neutral-50 flex items-center justify-center">
        <Icon className="h-4 w-4 text-neutral-400" />
      </div>
      <h3 className="text-base font-semibold text-neutral-900 mb-1">{title}</h3>
      <p className="text-sm text-neutral-500 max-w-sm mx-auto mb-4 leading-relaxed">{description}</p>
      {action}
    </div>
  )
}
