'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { FileText, Download, Eye, Clock, CheckCircle, XCircle, Bookmark, Trash2, ExternalLink } from 'lucide-react'
import { getSavedJobs, unsaveJob, Application as SavedApplication } from '@/lib/api/savedJobs'
import { toast } from 'react-hot-toast'

interface Application {
  id: string
  jobTitle: string
  company: string
  status: 'draft' | 'generated' | 'sent'
  createdAt: string
  updatedAt: string
  hasCV: boolean
  hasCoverLetter: boolean
  hasEmail: boolean
}

// Mock data
const mockApplications: Application[] = [
  {
    id: '1',
    jobTitle: 'Senior Software Engineer',
    company: 'Tech Corp',
    status: 'generated',
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    hasCV: true,
    hasCoverLetter: true,
    hasEmail: true,
  },
  {
    id: '2',
    jobTitle: 'Full Stack Developer',
    company: 'StartupXYZ',
    status: 'draft',
    createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    hasCV: true,
    hasCoverLetter: false,
    hasEmail: false,
  },
]

type TabType = 'saved' | 'draft' | 'submitted'

export default function ApplicationsPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<TabType>('saved')
  const [applications] = useState<Application[]>(mockApplications)
  const [savedJobs, setSavedJobs] = useState<SavedApplication[]>([])
  const [loadingSaved, setLoadingSaved] = useState(false)

  useEffect(() => {
    if (activeTab === 'saved') {
      loadSavedJobs()
    }
  }, [activeTab])

  const loadSavedJobs = async () => {
    try {
      setLoadingSaved(true)
      const jobs = await getSavedJobs()
      setSavedJobs(jobs)
    } catch (error) {
      console.error('Error loading saved jobs:', error)
      toast.error('Failed to load saved jobs')
    } finally {
      setLoadingSaved(false)
    }
  }

  const handleUnsave = async (jobId: string) => {
    try {
      await unsaveJob(jobId)
      setSavedJobs(prev => prev.filter(app => app.job_id !== jobId))
      toast.success('Job removed from saved')
    } catch (error) {
      console.error('Error removing saved job:', error)
      toast.error('Failed to remove job')
    }
  }

  const handleGenerateCV = (jobId: string) => {
    router.push(`/dashboard/applications/generate/${jobId}`)
  }

  const getDaysUntilExpiry = (expiresAt: string) => {
    const now = new Date()
    const expiry = new Date(expiresAt)
    const diffTime = expiry.getTime() - now.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays
  }

  const getStatusBadge = (status: Application['status']) => {
    const styles = {
      draft: 'bg-yellow-100 text-yellow-800',
      generated: 'bg-blue-100 text-blue-800',
      sent: 'bg-green-100 text-green-800',
    }
    const labels = {
      draft: 'Draft',
      generated: 'Ready',
      sent: 'Sent',
    }
    return (
      <span
        className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}
      >
        {labels[status]}
      </span>
    )
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-neutral-800 mb-2">
              My Applications
            </h1>
            <p className="text-neutral-600">
              Manage your job applications and generated materials
            </p>
          </div>

          {/* Tabs */}
          <div className="mb-6">
            <div className="border-b border-neutral-200">
              <nav className="flex space-x-8">
                <button
                  onClick={() => setActiveTab('saved')}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${activeTab === 'saved'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                    }
                  `}
                >
                  <div className="flex items-center space-x-2">
                    <Bookmark className="h-4 w-4" />
                    <span>Saved Jobs ({savedJobs.length})</span>
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('draft')}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${activeTab === 'draft'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                    }
                  `}
                >
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4" />
                    <span>In Progress ({applications.filter(a => a.status === 'draft' || a.status === 'generated').length})</span>
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('submitted')}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${activeTab === 'submitted'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300'
                    }
                  `}
                >
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4" />
                    <span>Submitted ({applications.filter(a => a.status === 'sent').length})</span>
                  </div>
                </button>
              </nav>
            </div>
          </div>

          {/* Saved Jobs Tab */}
          {activeTab === 'saved' && (
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200">
              {loadingSaved ? (
                <div className="p-12 text-center">
                  <Clock className="h-12 w-12 text-primary-600 mx-auto mb-4 animate-spin" />
                  <p className="text-neutral-600">Loading saved jobs...</p>
                </div>
              ) : savedJobs.length === 0 ? (
                <div className="p-12 text-center">
                  <Bookmark className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-neutral-600 mb-2">No saved jobs yet</p>
                  <p className="text-sm text-neutral-500">
                    Browse jobs and click the bookmark icon to save them for later
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-neutral-200">
                  {savedJobs.map((app) => {
                    const daysLeft = getDaysUntilExpiry(app.expires_at!)
                    return (
                      <div
                        key={app.id}
                        className="p-6 hover:bg-neutral-50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3 mb-2">
                              <h3 className="text-lg font-semibold text-neutral-800">
                                Saved Job
                              </h3>
                              {daysLeft <= 3 && (
                                <span className="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded-full font-medium">
                                  Expires in {daysLeft} day{daysLeft !== 1 ? 's' : ''}
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-neutral-500 mb-4">
                              Saved on {new Date(app.saved_at!).toLocaleDateString()}
                            </p>

                            <div className="flex items-center space-x-3">
                              <button
                                onClick={() => handleGenerateCV(app.job_id)}
                                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium text-sm"
                              >
                                Generate Tailored CV
                              </button>
                              <button
                                onClick={() => handleUnsave(app.job_id)}
                                className="px-4 py-2 border border-neutral-300 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors font-medium text-sm flex items-center space-x-2"
                              >
                                <Trash2 className="h-4 w-4" />
                                <span>Remove</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* In Progress Tab */}
          {activeTab === 'draft' && (
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200">
              {applications.filter(a => a.status === 'draft' || a.status === 'generated').length === 0 ? (
                <div className="p-12 text-center">
                  <Clock className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-neutral-600 mb-2">No applications in progress</p>
                  <p className="text-sm text-neutral-500">
                    Start by saving jobs and generating application materials
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-neutral-200">
                  {applications.filter(a => a.status === 'draft' || a.status === 'generated').map((application) => (
                    <div
                      key={application.id}
                      className="p-6 hover:bg-neutral-50 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="text-lg font-semibold text-neutral-800">
                              {application.jobTitle}
                            </h3>
                            {getStatusBadge(application.status)}
                          </div>
                          <p className="text-neutral-600 mb-4">{application.company}</p>

                          <div className="flex items-center space-x-4 mb-4">
                            <div className="flex items-center space-x-2">
                              {application.hasCV ? (
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              ) : (
                                <XCircle className="h-4 w-4 text-neutral-400" />
                              )}
                              <span className="text-sm text-neutral-600">CV</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              {application.hasCoverLetter ? (
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              ) : (
                                <XCircle className="h-4 w-4 text-neutral-400" />
                              )}
                              <span className="text-sm text-neutral-600">Cover Letter</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              {application.hasEmail ? (
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              ) : (
                                <XCircle className="h-4 w-4 text-neutral-400" />
                              )}
                              <span className="text-sm text-neutral-600">Email</span>
                            </div>
                          </div>

                          <div className="flex items-center space-x-4 text-xs text-neutral-500">
                            <span>Created: {formatDate(application.createdAt)}</span>
                            <span>Updated: {formatDate(application.updatedAt)}</span>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 ml-4">
                          <button
                            className="p-2 text-neutral-600 hover:text-neutral-800 hover:bg-neutral-100 rounded-lg transition-colors"
                            title="Preview"
                          >
                            <Eye className="h-5 w-5" />
                          </button>
                          <button
                            className="p-2 text-neutral-600 hover:text-neutral-800 hover:bg-neutral-100 rounded-lg transition-colors"
                            title="Download"
                          >
                            <Download className="h-5 w-5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Submitted Tab */}
          {activeTab === 'submitted' && (
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200">
              {applications.filter(a => a.status === 'sent').length === 0 ? (
                <div className="p-12 text-center">
                  <CheckCircle className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-neutral-600 mb-2">No submitted applications yet</p>
                  <p className="text-sm text-neutral-500">
                    Applications you mark as sent will appear here
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-neutral-200">
                  {applications.filter(a => a.status === 'sent').map((application) => (
                    <div
                      key={application.id}
                      className="p-6 hover:bg-neutral-50 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="text-lg font-semibold text-neutral-800">
                              {application.jobTitle}
                            </h3>
                            {getStatusBadge(application.status)}
                          </div>
                          <p className="text-neutral-600 mb-4">{application.company}</p>

                          <div className="flex items-center space-x-4 text-xs text-neutral-500">
                            <span>Created: {formatDate(application.createdAt)}</span>
                            <span>Submitted: {formatDate(application.updatedAt)}</span>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 ml-4">
                          <button
                            className="p-2 text-neutral-600 hover:text-neutral-800 hover:bg-neutral-100 rounded-lg transition-colors"
                            title="Preview"
                          >
                            <Eye className="h-5 w-5" />
                          </button>
                          <button
                            className="p-2 text-neutral-600 hover:text-neutral-800 hover:bg-neutral-100 rounded-lg transition-colors"
                            title="Download"
                          >
                            <Download className="h-5 w-5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

