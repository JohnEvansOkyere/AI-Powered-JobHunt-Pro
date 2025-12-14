'use client'

import { useState } from 'react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { FileText, Download, Eye, Clock, CheckCircle, XCircle } from 'lucide-react'

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

export default function ApplicationsPage() {
  const [applications] = useState<Application[]>(mockApplications)

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

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-neutral-600">Total</p>
                  <p className="text-2xl font-bold text-neutral-800">
                    {applications.length}
                  </p>
                </div>
                <FileText className="h-8 w-8 text-primary-600" />
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-neutral-600">Ready</p>
                  <p className="text-2xl font-bold text-neutral-800">
                    {applications.filter((a) => a.status === 'generated').length}
                  </p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-neutral-600">Drafts</p>
                  <p className="text-2xl font-bold text-neutral-800">
                    {applications.filter((a) => a.status === 'draft').length}
                  </p>
                </div>
                <Clock className="h-8 w-8 text-yellow-600" />
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-neutral-600">Sent</p>
                  <p className="text-2xl font-bold text-neutral-800">
                    {applications.filter((a) => a.status === 'sent').length}
                  </p>
                </div>
                <CheckCircle className="h-8 w-8 text-blue-600" />
              </div>
            </div>
          </div>

          {/* Applications List */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200">
            {applications.length === 0 ? (
              <div className="p-12 text-center">
                <FileText className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                <p className="text-neutral-600 mb-2">No applications yet</p>
                <p className="text-sm text-neutral-500">
                  Start by finding jobs and generating application materials
                </p>
              </div>
            ) : (
              <div className="divide-y divide-neutral-200">
                {applications.map((application) => (
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

                        {/* Materials */}
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
                            <span className="text-sm text-neutral-600">
                              Cover Letter
                            </span>
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

                      {/* Actions */}
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
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

