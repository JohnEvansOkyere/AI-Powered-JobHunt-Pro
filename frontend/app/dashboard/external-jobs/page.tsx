'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { searchJobs, deleteJob, type Job } from '@/lib/api/jobs'
import { ExternalLink, Zap, Trash2, Eye, Loader2, Plus, Briefcase, MapPin, DollarSign, Clock, Building2 } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { motion } from 'framer-motion'
import { AddExternalJobModal } from '@/components/modals/AddExternalJobModal'
import { parseJsonArray } from '@/lib/utils/jsonParser'

export default function ExternalJobsPage() {
  const router = useRouter()
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null)

  useEffect(() => {
    loadExternalJobs()
  }, [])

  const loadExternalJobs = async () => {
    try {
      setLoading(true)
      // Filter for external jobs only
      const response = await searchJobs({ source: 'external', page: 1, page_size: 100 })
      setJobs(response.jobs)
    } catch (error) {
      console.error('Error loading external jobs:', error)
      toast.error('Failed to load your jobs')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateCV = (jobId: string) => {
    router.push(`/dashboard/applications/generate/${jobId}`)
  }

  const handleViewDetails = (jobId: string) => {
    router.push(`/dashboard/jobs/${jobId}`)
  }

  const handleDeleteJob = async (jobId: string, jobTitle: string) => {
    const confirmMessage = `Are you sure you want to delete "${jobTitle}"?\n\nThis will also delete any generated CVs and cover letters for this job.\n\nThis action cannot be undone.`
    
    if (!confirm(confirmMessage)) {
      return
    }

    try {
      setDeletingJobId(jobId)
      await deleteJob(jobId)
      toast.success('Job and associated materials deleted successfully')
      // Remove from local state
      setJobs(jobs.filter(j => j.id !== jobId))
    } catch (error: any) {
      console.error('Error deleting job:', error)
      
      // Handle specific error cases
      if (error.status === 404) {
        // Job already deleted or doesn't exist - just remove from UI
        toast.success('Job removed')
        setJobs(jobs.filter(j => j.id !== jobId))
      } else if (error.status === 403) {
        toast.error('You do not have permission to delete this job')
      } else {
        toast.error(error.message || 'Failed to delete job')
      }
    } finally {
      setDeletingJobId(null)
    }
  }

  const formatSalary = (job: Job) => {
    if (job.salary_min && job.salary_max) {
      return `${job.salary_currency || ''} ${job.salary_min} - ${job.salary_max}`
    } else if (job.salary_max) {
      return `Up to ${job.salary_currency || ''} ${job.salary_max}`
    } else if (job.salary_range) {
      return job.salary_range
    }
    return null
  }


  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-black text-neutral-900 mb-2">
                My External Jobs
              </h1>
              <p className="text-neutral-600 text-lg">
                Jobs you've manually added from LinkedIn, Indeed, and other sources
              </p>
            </div>
            <button
              onClick={() => setIsModalOpen(true)}
              className="btn-premium px-6 py-3 bg-brand-orange-500 text-white rounded-2xl font-black flex items-center space-x-2 shadow-lg shadow-brand-orange-500/20 hover:shadow-xl hover:shadow-brand-orange-500/30 transition-all"
            >
              <Plus className="w-5 h-5" />
              <span>Add New Job</span>
            </button>
          </div>

          {/* Stats */}
          {!loading && jobs.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white rounded-2xl p-6 border border-neutral-100 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">Total Jobs</p>
                    <p className="text-3xl font-black text-neutral-900">{jobs.length}</p>
                  </div>
                  <div className="w-12 h-12 bg-brand-turquoise-50 rounded-xl flex items-center justify-center">
                    <Briefcase className="w-6 h-6 text-brand-turquoise-600" />
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-2xl p-6 border border-neutral-100 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">Remote Jobs</p>
                    <p className="text-3xl font-black text-neutral-900">
                      {jobs.filter(j => j.remote_option === 'True' || j.remote_type === 'remote').length}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-brand-orange-50 rounded-xl flex items-center justify-center">
                    <MapPin className="w-6 h-6 text-brand-orange-600" />
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-2xl p-6 border border-neutral-100 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-1">This Week</p>
                    <p className="text-3xl font-black text-neutral-900">
                      {jobs.filter(j => {
                        const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
                        return new Date(j.created_at) > weekAgo
                      }).length}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-brand-turquoise-50 rounded-xl flex items-center justify-center">
                    <Clock className="w-6 h-6 text-brand-turquoise-600" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Jobs List */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-12 w-12 text-brand-turquoise-600 animate-spin" />
            </div>
          ) : jobs.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white rounded-3xl p-12 border border-neutral-100 text-center"
            >
              <div className="w-20 h-20 bg-brand-orange-50 rounded-full flex items-center justify-center mx-auto mb-6">
                <Plus className="w-10 h-10 text-brand-orange-600" />
              </div>
              <h3 className="text-2xl font-black text-neutral-900 mb-3">No External Jobs Yet</h3>
              <p className="text-neutral-600 mb-8 max-w-md mx-auto">
                Start adding jobs from LinkedIn, Indeed, or any job board. Our AI will extract all the details automatically.
              </p>
              <button
                onClick={() => setIsModalOpen(true)}
                className="btn-premium px-8 py-4 bg-brand-orange-500 text-white rounded-2xl font-black text-lg shadow-xl shadow-brand-orange-500/20 inline-flex items-center space-x-3"
              >
                <Plus className="w-6 h-6" />
                <span>Add Your First Job</span>
              </button>
            </motion.div>
          ) : (
            <div className="space-y-4">
              {jobs.map((job, index) => {
                const skills = parseJsonArray(job.skills)
                const requirements = parseJsonArray(job.requirements)
                const salary = formatSalary(job)

                return (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="bg-white rounded-2xl p-6 md:p-8 border border-neutral-100 hover:border-brand-turquoise-200 hover:shadow-xl transition-all duration-300 group"
                  >
                    <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
                      {/* Job Info */}
                      <div className="flex-1 space-y-4">
                        {/* Title & Company */}
                        <div>
                          <div className="flex items-start gap-3 mb-2">
                            <div className="w-12 h-12 bg-brand-turquoise-50 rounded-xl flex items-center justify-center flex-shrink-0">
                              <Building2 className="w-6 h-6 text-brand-turquoise-600" />
                            </div>
                            <div className="flex-1">
                              <h3 className="text-xl md:text-2xl font-bold text-neutral-900 mb-1 group-hover:text-brand-turquoise-600 transition-colors">
                                {job.title}
                              </h3>
                              <p className="text-lg font-semibold text-neutral-700">{job.company}</p>
                            </div>
                          </div>
                        </div>

                        {/* Meta Info */}
                        <div className="flex flex-wrap items-center gap-3 text-sm">
                          {job.location && (
                            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-50 rounded-lg">
                              <MapPin className="w-4 h-4 text-neutral-500" />
                              <span className="text-neutral-700 font-medium">{job.location}</span>
                            </div>
                          )}
                          {salary && (
                            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-50 rounded-lg">
                              <DollarSign className="w-4 h-4 text-green-600" />
                              <span className="text-green-700 font-bold">{salary}</span>
                            </div>
                          )}
                          {job.job_type && (
                            <span className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg font-medium capitalize">
                              {job.job_type}
                            </span>
                          )}
                          {(job.remote_option === 'True' || job.remote_type === 'remote') && (
                            <span className="px-3 py-1.5 bg-purple-50 text-purple-700 rounded-lg font-medium">
                              Remote
                            </span>
                          )}
                          {job.experience_level && (
                            <span className="px-3 py-1.5 bg-orange-50 text-orange-700 rounded-lg font-medium capitalize">
                              {job.experience_level}
                            </span>
                          )}
                        </div>

                        {/* Skills */}
                        {skills.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-2">Required Skills</p>
                            <div className="flex flex-wrap gap-2">
                              {skills.slice(0, 6).map((skill, i) => (
                                <span key={i} className="px-3 py-1 bg-brand-turquoise-50 text-brand-turquoise-700 rounded-full text-sm font-medium">
                                  {skill}
                                </span>
                              ))}
                              {skills.length > 6 && (
                                <span className="px-3 py-1 bg-neutral-100 text-neutral-600 rounded-full text-sm font-medium">
                                  +{skills.length - 6} more
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Requirements Preview */}
                        {requirements.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-2">Top Requirements</p>
                            <ul className="space-y-1">
                              {requirements.slice(0, 3).map((req, i) => (
                                <li key={i} className="text-sm text-neutral-600 flex items-start gap-2">
                                  <span className="text-brand-orange-500 mt-1">•</span>
                                  <span>{req}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Source */}
                        {job.source_url && (
                          <a
                            href={job.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 text-sm text-brand-turquoise-600 hover:text-brand-turquoise-700 font-medium"
                          >
                            <ExternalLink className="w-4 h-4" />
                            <span>View Original Posting</span>
                          </a>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex lg:flex-col gap-3 lg:min-w-[200px]">
                        <button
                          onClick={() => handleGenerateCV(job.id)}
                          className="flex-1 lg:w-full btn-premium px-6 py-4 bg-gradient-to-r from-brand-orange-500 to-brand-orange-600 text-white rounded-2xl font-black text-sm shadow-lg shadow-brand-orange-500/20 hover:shadow-xl hover:shadow-brand-orange-500/30 transition-all flex items-center justify-center gap-2"
                        >
                          <Zap className="w-5 h-5 fill-white" />
                          <span>Generate CV</span>
                        </button>
                        <button
                          onClick={() => handleViewDetails(job.id)}
                          className="flex-1 lg:w-full px-6 py-4 bg-brand-turquoise-50 text-brand-turquoise-600 rounded-2xl font-bold text-sm hover:bg-brand-turquoise-100 transition-all flex items-center justify-center gap-2"
                        >
                          <Eye className="w-5 h-5" />
                          <span>View Details</span>
                        </button>
                        <button
                          onClick={() => handleDeleteJob(job.id, job.title)}
                          disabled={deletingJobId === job.id}
                          className="flex-1 lg:w-full px-6 py-4 bg-red-50 text-red-600 rounded-2xl font-bold text-sm hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                        >
                          {deletingJobId === job.id ? (
                            <>
                              <Loader2 className="w-5 h-5 animate-spin" />
                              <span>Deleting...</span>
                            </>
                          ) : (
                            <>
                              <Trash2 className="w-5 h-5" />
                              <span>Delete</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}
        </div>

        {/* Add External Job Modal */}
        <AddExternalJobModal 
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            loadExternalJobs()
          }}
        />
      </DashboardLayout>
    </ProtectedRoute>
  )
}
