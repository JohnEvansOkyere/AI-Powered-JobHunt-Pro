'use client'

import { useState, useEffect } from 'react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { uploadCV, getCVs, getActiveCV, deleteCV, getCVDownloadURL, CV, CVDetail } from '@/lib/api/cvs'
import { Upload, FileText, Download, Trash2, CheckCircle, XCircle, Loader, AlertCircle, Sparkles } from 'lucide-react'
import { toast } from 'react-hot-toast'
import Link from 'next/link'

export default function CVPage() {
  const [cvs, setCVs] = useState<CV[]>([])
  const [activeCV, setActiveCV] = useState<CVDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  useEffect(() => {
    loadCVs()
  }, [])

  const loadCVs = async () => {
    try {
      setLoading(true)
      const [cvsList, active] = await Promise.all([getCVs(), getActiveCV()])
      setCVs(cvsList)
      setActiveCV(active)
    } catch (error) {
      console.error('Error loading CVs:', error)
      toast.error('Failed to load CVs')
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = async (file: File) => {
    // Validate file type
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    const allowedExtensions = ['.pdf', '.docx']
    
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    
    if (!allowedExtensions.includes(fileExtension)) {
      toast.error('Invalid file type. Please upload a PDF or DOCX file.')
      return
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large. Maximum size is 10MB.')
      return
    }

    try {
      setUploading(true)
      const uploadedCV = await uploadCV(file)
      toast.success('CV uploaded successfully! Parsing in progress...')
      await loadCVs()
    } catch (error: any) {
      console.error('Error uploading CV:', error)
      toast.error(error.response?.data?.detail || 'Failed to upload CV')
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)

    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDelete = async (cvId: string) => {
    if (!confirm('Are you sure you want to delete this CV?')) {
      return
    }

    try {
      await deleteCV(cvId)
      toast.success('CV deleted successfully')
      await loadCVs()
    } catch (error: any) {
      console.error('Error deleting CV:', error)
      const errorMessage = error.response?.data?.detail || 'Failed to delete CV'

      // If CV not found, it might be stale data - refresh the list
      if (error.response?.status === 404 || errorMessage.includes('not found')) {
        toast.error('CV not found. Refreshing list...')
        await loadCVs()
      } else {
        toast.error(errorMessage)
      }
    }
  }

  const handleDownload = async (cvId: string, fileName: string) => {
    try {
      const { download_url } = await getCVDownloadURL(cvId)
      window.open(download_url, '_blank')
    } catch (error: any) {
      console.error('Error downloading CV:', error)
      toast.error('Failed to generate download link')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'processing':
        return <Loader className="h-5 w-5 text-blue-600 animate-spin" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-600" />
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-600" />
    }
  }

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-neutral-800 mb-2">CV Management</h1>
            <p className="text-neutral-600">Upload and manage your CV files</p>
            
            {/* Custom CV Generation Link */}
            <div className="mt-4 flex items-center space-x-3">
              <Link
                href="/dashboard/cv/custom"
                className="inline-flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <Sparkles className="h-4 w-4" />
                <span>AI Generator (Paste Any Job)</span>
              </Link>
              <p className="text-sm text-neutral-500">
                Generate tailored CV & cover letter from any job link or description
              </p>
            </div>
          </div>

          {/* Upload Area */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                dragActive
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-neutral-300 hover:border-primary-400'
              }`}
            >
              <Upload className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-neutral-800 mb-2">
                Upload Your CV
              </h3>
              <p className="text-sm text-neutral-600 mb-4">
                Drag and drop your CV file here, or click to browse
              </p>
              <p className="text-xs text-neutral-500 mb-2">
                Supported formats: PDF, DOCX (Max 10MB)
              </p>

              {/* DOCX Recommendation Notice */}
              <div className="mb-4 mx-auto max-w-2xl bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-start space-x-2">
                  <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-blue-900 mb-1">
                      💡 Recommended: Upload DOCX format
                    </p>
                    <p className="text-xs text-blue-700">
                      For best results with tailored CV generation, upload a DOCX file.
                      DOCX files preserve your original formatting when we create job-specific versions.
                      PDF files will be converted to a new format.
                    </p>
                  </div>
                </div>
              </div>

              <label className="inline-block">
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={handleFileInput}
                  disabled={uploading}
                  className="hidden"
                />
                <span className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors cursor-pointer inline-block disabled:opacity-50">
                  {uploading ? 'Uploading...' : 'Choose File'}
                </span>
              </label>
            </div>
          </div>

          {/* Active CV Preview */}
          {activeCV && (
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <FileText className="h-6 w-6 text-primary-600" />
                  <div>
                    <h2 className="text-lg font-semibold text-neutral-800">Active CV</h2>
                    <p className="text-sm text-neutral-600">{activeCV.file_name}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(activeCV.parsing_status)}
                  <span className="text-sm text-neutral-600 capitalize">
                    {activeCV.parsing_status}
                  </span>
                </div>
              </div>

              {activeCV.parsing_status === 'completed' && activeCV.parsed_content && (
                <div className="mt-4 pt-4 border-t border-neutral-200">
                  <h3 className="font-semibold text-neutral-800 mb-3">Extracted Information</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    {activeCV.parsed_content.personal_info?.name && (
                      <div>
                        <span className="text-neutral-500">Name:</span>{' '}
                        <span className="font-medium">{activeCV.parsed_content.personal_info.name}</span>
                      </div>
                    )}
                    {activeCV.parsed_content.personal_info?.email && (
                      <div>
                        <span className="text-neutral-500">Email:</span>{' '}
                        <span className="font-medium">{activeCV.parsed_content.personal_info.email}</span>
                      </div>
                    )}
                    {activeCV.parsed_content.experience && 
                     Array.isArray(activeCV.parsed_content.experience) && 
                     activeCV.parsed_content.experience.length > 0 && (
                      <div>
                        <span className="text-neutral-500">Experience:</span>{' '}
                        <span className="font-medium">{activeCV.parsed_content.experience.length} positions</span>
                      </div>
                    )}
                    {activeCV.parsed_content.education && 
                     Array.isArray(activeCV.parsed_content.education) && 
                     activeCV.parsed_content.education.length > 0 && (
                      <div>
                        <span className="text-neutral-500">Education:</span>{' '}
                        <span className="font-medium">{activeCV.parsed_content.education.length} entries</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeCV.parsing_status === 'failed' && activeCV.parsing_error && (
                <div className="mt-4 pt-4 border-t border-neutral-200">
                  <p className="text-sm text-red-600">Error: {activeCV.parsing_error}</p>
                </div>
              )}

              <div className="mt-4 pt-4 border-t border-neutral-200 flex items-center space-x-3">
                <button
                  onClick={() => handleDownload(activeCV.id, activeCV.file_name)}
                  className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-primary-600 hover:text-primary-700"
                >
                  <Download className="h-4 w-4" />
                  <span>Download</span>
                </button>
                <button
                  onClick={() => handleDelete(activeCV.id)}
                  className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Delete</span>
                </button>
              </div>
            </div>
          )}

          {/* All CVs List */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200">
            <div className="p-6 border-b border-neutral-200">
              <h2 className="text-lg font-semibold text-neutral-800">All CVs</h2>
            </div>

            {loading ? (
              <div className="p-12 text-center">
                <Loader className="h-8 w-8 text-primary-600 animate-spin mx-auto mb-4" />
                <p className="text-neutral-600">Loading CVs...</p>
              </div>
            ) : cvs.length === 0 ? (
              <div className="p-12 text-center">
                <FileText className="h-12 w-12 text-neutral-400 mx-auto mb-4" />
                <p className="text-neutral-600 mb-2">No CVs uploaded yet</p>
                <p className="text-sm text-neutral-500">Upload your first CV to get started</p>
              </div>
            ) : (
              <div className="divide-y divide-neutral-200">
                {cvs.map((cv) => (
                  <div key={cv.id} className="p-6 hover:bg-neutral-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 flex-1">
                        <FileText className="h-8 w-8 text-neutral-400" />
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-1">
                            <h3 className="font-semibold text-neutral-800">{cv.file_name}</h3>
                            {cv.is_active && (
                              <span className="px-2 py-1 text-xs font-medium bg-primary-100 text-primary-700 rounded-full">
                                Active
                              </span>
                            )}
                            {getStatusIcon(cv.parsing_status)}
                          </div>
                          <div className="flex items-center space-x-4 text-sm text-neutral-600">
                            <span>{formatFileSize(cv.file_size)}</span>
                            <span className="capitalize">{cv.file_type}</span>
                            <span>
                              {new Date(cv.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleDownload(cv.id, cv.file_name)}
                          className="p-2 text-neutral-600 hover:text-neutral-800 hover:bg-neutral-100 rounded-lg transition-colors"
                          title="Download"
                        >
                          <Download className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => handleDelete(cv.id)}
                          className="p-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="h-5 w-5" />
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

