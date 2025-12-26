'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { generateTailoredCV, getApplicationForJob, getCVDownloadUrl, type GenerateCVRequest } from '@/lib/api/applications'
import { getJob } from '@/lib/api/jobs'
import { Loader, CheckCircle, Download, ArrowLeft, FileText } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function GenerateApplicationPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.jobId as string
  
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [job, setJob] = useState<any>(null)
  const [existingApplication, setExistingApplication] = useState<any>(null)
  const [generationSettings, setGenerationSettings] = useState<GenerateCVRequest>({
    tone: 'professional',
    highlight_skills: true,
    emphasize_relevant_experience: true,
  })
  const [generatedCV, setGeneratedCV] = useState<any>(null)

  useEffect(() => {
    loadData()
  }, [jobId])

  const loadData = async () => {
    try {
      setLoading(true)
      
      // Load job details
      const jobData = await getJob(jobId)
      setJob(jobData)
      
      // Check for existing application
      try {
        const app = await getApplicationForJob(jobId)
        if (app) {
          setExistingApplication(app)
          if (app.tailored_cv_path) {
            // Get download URL
            const urlData = await getCVDownloadUrl(app.id)
            setGeneratedCV({
              application_id: app.id,
              public_url: urlData.download_url,
              status: app.status,
            })
          }
        }
      } catch (e) {
        // No existing application - that's fine
      }
    } catch (error: any) {
      console.error('Error loading data:', error)
      toast.error('Failed to load job details')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    try {
      setGenerating(true)
      const result = await generateTailoredCV(jobId, generationSettings)
      setGeneratedCV(result)
      toast.success('CV generated successfully!')
      
      // Reload to get updated application
      await loadData()
    } catch (error: any) {
      console.error('Error generating CV:', error)
      toast.error(error.message || 'Failed to generate tailored CV')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = () => {
    if (generatedCV?.public_url) {
      window.open(generatedCV.public_url, '_blank')
    }
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center min-h-[400px]">
            <Loader className="h-8 w-8 text-primary-600 animate-spin" />
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (!job) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="max-w-4xl mx-auto">
            <p className="text-neutral-600">Job not found</p>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <button
              onClick={() => router.back()}
              className="flex items-center text-neutral-600 hover:text-neutral-800 mb-4"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Jobs
            </button>
            <h1 className="text-3xl font-bold text-neutral-800 mb-2">
              Generate Tailored CV
            </h1>
            <p className="text-neutral-600">
              For: <span className="font-semibold">{job.title}</span> at <span className="font-semibold">{job.company}</span>
            </p>
          </div>

          {/* Generation Settings */}
          {!generatedCV && (
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
              <h2 className="text-xl font-semibold text-neutral-800 mb-4">
                Generation Settings
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-2">
                    Writing Tone
                  </label>
                  <select
                    value={generationSettings.tone}
                    onChange={(e) => setGenerationSettings({
                      ...generationSettings,
                      tone: e.target.value as 'professional' | 'confident' | 'friendly'
                    })}
                    className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="professional">Professional</option>
                    <option value="confident">Confident</option>
                    <option value="friendly">Friendly</option>
                  </select>
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="highlight_skills"
                    checked={generationSettings.highlight_skills}
                    onChange={(e) => setGenerationSettings({
                      ...generationSettings,
                      highlight_skills: e.target.checked
                    })}
                    className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500"
                  />
                  <label htmlFor="highlight_skills" className="text-sm text-neutral-700">
                    Highlight relevant skills
                  </label>
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="emphasize_experience"
                    checked={generationSettings.emphasize_relevant_experience}
                    onChange={(e) => setGenerationSettings({
                      ...generationSettings,
                      emphasize_relevant_experience: e.target.checked
                    })}
                    className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500"
                  />
                  <label htmlFor="emphasize_experience" className="text-sm text-neutral-700">
                    Emphasize relevant experience
                  </label>
                </div>
              </div>

              <button
                onClick={handleGenerate}
                disabled={generating}
                className="mt-6 w-full px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {generating ? (
                  <>
                    <Loader className="h-5 w-5 mr-2 animate-spin" />
                    Generating CV...
                  </>
                ) : (
                  <>
                    <FileText className="h-5 w-5 mr-2" />
                    Generate Tailored CV
                  </>
                )}
              </button>
            </div>
          )}

          {/* Success State */}
          {generatedCV && (
            <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
              <div className="flex items-start space-x-4 mb-6">
                <div className="flex-shrink-0">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-semibold text-neutral-800 mb-2">
                    CV Generated Successfully!
                  </h2>
                  <p className="text-neutral-600">
                    Your tailored CV has been generated and is ready to download.
                  </p>
                </div>
              </div>

              <div className="flex space-x-4">
                <button
                  onClick={handleDownload}
                  className="flex-1 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium flex items-center justify-center"
                >
                  <Download className="h-5 w-5 mr-2" />
                  Download CV
                </button>
                <button
                  onClick={() => router.push('/dashboard/applications')}
                  className="px-4 py-3 border border-neutral-300 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors font-medium"
                >
                  View All Applications
                </button>
              </div>

              {existingApplication && (
                <div className="mt-6 pt-6 border-t border-neutral-200">
                  <p className="text-sm text-neutral-600">
                    Status: <span className="font-medium capitalize">{existingApplication.status}</span>
                  </p>
                  <p className="text-sm text-neutral-600 mt-1">
                    Generated: {new Date(existingApplication.created_at).toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Job Preview */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mt-6">
            <h3 className="text-lg font-semibold text-neutral-800 mb-4">
              Job Details
            </h3>
            <div className="space-y-2 text-sm text-neutral-600">
              <p><span className="font-medium">Company:</span> {job.company}</p>
              <p><span className="font-medium">Location:</span> {job.location || 'Not specified'}</p>
              <p><span className="font-medium">Type:</span> {job.job_type || 'Not specified'}</p>
              {job.remote_type && (
                <p><span className="font-medium">Remote:</span> {job.remote_type}</p>
              )}
            </div>
            {job.description && (
              <div className="mt-4">
                <p className="text-sm font-medium text-neutral-700 mb-2">Description:</p>
                <div 
                  className="text-sm text-neutral-600 line-clamp-4"
                  dangerouslySetInnerHTML={{ __html: job.description.substring(0, 500) + '...' }}
                />
              </div>
            )}
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}


