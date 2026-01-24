'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { generateCustomTailoredCV, generateCustomCoverLetter } from '@/lib/api/applications'
import { getActiveCV, CVDetail } from '@/lib/api/cvs'
import { FileText, Mail, AlertCircle, Loader, CheckCircle, ArrowLeft, Link as LinkIcon, FileEdit, Sparkles } from 'lucide-react'
import { toast } from 'react-hot-toast'
import Link from 'next/link'

export default function CustomCVGenerationPage() {
  const router = useRouter()
  const [activeCV, setActiveCV] = useState<CVDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [generatingCV, setGeneratingCV] = useState(false)
  const [generatingCoverLetter, setGeneratingCoverLetter] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [coverLetterText, setCoverLetterText] = useState<string | null>(null)
  
  // Form state - SIMPLIFIED
  const [inputMode, setInputMode] = useState<'description' | 'link'>('link')
  const [jobLink, setJobLink] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [companyName, setCompanyName] = useState('')
  
  // Advanced options - collapsed by default
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [tone, setTone] = useState<'professional' | 'confident' | 'friendly' | 'enthusiastic'>('professional')
  const [coverLetterLength, setCoverLetterLength] = useState<'short' | 'medium' | 'long'>('medium')

  useEffect(() => {
    loadActiveCV()
  }, [])

  const loadActiveCV = async () => {
    try {
      setLoading(true)
      const cv = await getActiveCV()
      setActiveCV(cv)
      
      if (!cv) {
        toast.error('No active CV found. Please upload a CV first.')
      }
    } catch (error) {
      console.error('Error loading CV:', error)
      toast.error('Failed to load CV')
    } finally {
      setLoading(false)
    }
  }

  const validateInput = () => {
    if (inputMode === 'link') {
      if (!jobLink.trim()) {
        toast.error('Please enter a job posting URL')
        return false
      }
      // Basic URL validation
      try {
        new URL(jobLink.trim())
      } catch {
        toast.error('Please enter a valid URL (e.g., https://...)')
        return false
      }
    } else {
      if (!jobDescription.trim()) {
        toast.error('Please enter a job description')
        return false
      }
      if (!jobTitle.trim()) {
        toast.error('Job title is required when pasting description')
        return false
      }
      if (!companyName.trim()) {
        toast.error('Company name is required when pasting description')
        return false
      }
    }
    return true
  }

  const handleGenerateCV = async () => {
    if (!activeCV || activeCV.parsing_status !== 'completed') {
      toast.error('Please wait for your CV to finish parsing')
      return
    }

    if (!validateInput()) return

    try {
      setGeneratingCV(true)
      setDownloadUrl(null)

      const result = await generateCustomTailoredCV({
        job_title: jobTitle.trim() || undefined as any,
        company_name: companyName.trim() || undefined as any,
        job_description: inputMode === 'description' ? jobDescription.trim() : undefined,
        job_link: inputMode === 'link' ? jobLink.trim() : undefined,
        tone,
        highlight_skills: true,
        emphasize_relevant_experience: true,
      })

      toast.success('CV generated successfully!')
      
      if (result.public_url) {
        setDownloadUrl(result.public_url)
      }

    } catch (error: any) {
      console.error('Error generating CV:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to generate CV'
      toast.error(errorMessage)
    } finally {
      setGeneratingCV(false)
    }
  }

  const handleGenerateCoverLetter = async () => {
    if (!activeCV || activeCV.parsing_status !== 'completed') {
      toast.error('Please wait for your CV to finish parsing')
      return
    }

    if (!validateInput()) return

    try {
      setGeneratingCoverLetter(true)
      setCoverLetterText(null)

      const result = await generateCustomCoverLetter({
        job_title: jobTitle.trim() || undefined as any,
        company_name: companyName.trim() || undefined as any,
        job_description: inputMode === 'description' ? jobDescription.trim() : undefined,
        job_link: inputMode === 'link' ? jobLink.trim() : undefined,
        tone,
        length: coverLetterLength,
      })

      toast.success('Cover letter generated successfully!')
      
      if (result.cover_letter) {
        setCoverLetterText(result.cover_letter)
      }

    } catch (error: any) {
      console.error('Error generating cover letter:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to generate cover letter'
      toast.error(errorMessage)
    } finally {
      setGeneratingCoverLetter(false)
    }
  }

  const handleReset = () => {
    setJobLink('')
    setJobDescription('')
    setJobTitle('')
    setCompanyName('')
    setDownloadUrl(null)
    setCoverLetterText(null)
  }

  const copyCoverLetterToClipboard = () => {
    if (coverLetterText) {
      navigator.clipboard.writeText(coverLetterText)
      toast.success('Cover letter copied to clipboard!')
    }
  }

  const isGenerating = generatingCV || generatingCoverLetter

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

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-5xl mx-auto">
          {/* Back button */}
          <Link 
            href="/dashboard/cv"
            className="inline-flex items-center space-x-2 text-neutral-600 hover:text-neutral-800 mb-6 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to CV Management</span>
          </Link>

          {/* Header - SIMPLIFIED */}
          <div className="mb-8 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-100 mb-4">
              <Sparkles className="h-8 w-8 text-primary-600" />
            </div>
            <h1 className="text-4xl font-bold text-neutral-900 mb-3">
              AI-Powered Application Generator
            </h1>
            <p className="text-lg text-neutral-600 max-w-2xl mx-auto">
              Paste a job link or description to instantly generate a tailored CV and cover letter
            </p>
          </div>

          {/* CV Status - COMPACT */}
          {activeCV ? (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
              <div className="flex items-center space-x-3">
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-green-900">
                    CV Ready: {activeCV.file_name}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
              <div className="flex items-center space-x-3">
                <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-yellow-900">No CV Found</p>
                  <p className="text-xs text-yellow-700 mt-1">
                    <Link href="/dashboard/cv" className="underline font-medium">
                      Upload a CV
                    </Link>{' '}
                    to get started
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Main Input Card - CLEAN & PROFESSIONAL */}
          <div className="bg-white rounded-2xl shadow-lg border border-neutral-200 overflow-hidden mb-6">
            {/* Input Mode Toggle - PROMINENT */}
            <div className="border-b border-neutral-200 bg-neutral-50 p-6">
              <label className="block text-sm font-semibold text-neutral-700 mb-3">
                Choose Input Method
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setInputMode('link')}
                  disabled={isGenerating}
                  className={`flex items-center justify-center space-x-2 px-6 py-4 rounded-xl font-medium transition-all ${
                    inputMode === 'link'
                      ? 'bg-primary-600 text-white shadow-md'
                      : 'bg-white text-neutral-700 border-2 border-neutral-300 hover:border-primary-400'
                  } disabled:opacity-50`}
                >
                  <LinkIcon className="h-5 w-5" />
                  <span>Paste Job Link</span>
                </button>
                <button
                  type="button"
                  onClick={() => setInputMode('description')}
                  disabled={isGenerating}
                  className={`flex items-center justify-center space-x-2 px-6 py-4 rounded-xl font-medium transition-all ${
                    inputMode === 'description'
                      ? 'bg-primary-600 text-white shadow-md'
                      : 'bg-white text-neutral-700 border-2 border-neutral-300 hover:border-primary-400'
                  } disabled:opacity-50`}
                >
                  <FileEdit className="h-5 w-5" />
                  <span>Paste Description</span>
                </button>
              </div>
            </div>

            <div className="p-6">
              {inputMode === 'link' ? (
                /* JOB LINK INPUT - SIMPLE */
                <div>
                  <label htmlFor="jobLink" className="block text-sm font-semibold text-neutral-700 mb-3">
                    Job Posting URL
                  </label>
                  <input
                    type="url"
                    id="jobLink"
                    value={jobLink}
                    onChange={(e) => setJobLink(e.target.value)}
                    placeholder="https://linkedin.com/jobs/view/... or any job board link"
                    disabled={isGenerating || !activeCV}
                    className="w-full px-4 py-3 text-lg border-2 border-neutral-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50 transition-all"
                  />
                  <p className="text-xs text-neutral-500 mt-2 flex items-start space-x-1">
                    <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                    <span>
                      Supports LinkedIn, Indeed, Glassdoor, and most job boards. The AI will automatically extract job details.
                    </span>
                  </p>
                </div>
              ) : (
                /* JOB DESCRIPTION INPUT - CLEAN */
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="jobTitle" className="block text-sm font-semibold text-neutral-700 mb-2">
                        Job Title *
                      </label>
                      <input
                        type="text"
                        id="jobTitle"
                        value={jobTitle}
                        onChange={(e) => setJobTitle(e.target.value)}
                        placeholder="e.g., Senior Software Engineer"
                        disabled={isGenerating || !activeCV}
                        className="w-full px-4 py-3 border-2 border-neutral-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
                      />
                    </div>
                    <div>
                      <label htmlFor="companyName" className="block text-sm font-semibold text-neutral-700 mb-2">
                        Company Name *
                      </label>
                      <input
                        type="text"
                        id="companyName"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        placeholder="e.g., Tech Corp"
                        disabled={isGenerating || !activeCV}
                        className="w-full px-4 py-3 border-2 border-neutral-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="jobDescription" className="block text-sm font-semibold text-neutral-700 mb-2">
                      Job Description *
                    </label>
                    <textarea
                      id="jobDescription"
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      placeholder="Paste the complete job description here..."
                      disabled={isGenerating || !activeCV}
                      rows={10}
                      className="w-full px-4 py-3 border-2 border-neutral-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50 resize-y"
                    />
                  </div>
                </div>
              )}

              {/* Advanced Options - COLLAPSIBLE */}
              <div className="mt-6 pt-6 border-t border-neutral-200">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="text-sm font-medium text-primary-600 hover:text-primary-700 flex items-center space-x-1"
                >
                  <span>{showAdvanced ? '▼' : '▶'}</span>
                  <span>Advanced Options</span>
                </button>

                {showAdvanced && (
                  <div className="mt-4 grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="tone" className="block text-sm font-medium text-neutral-700 mb-2">
                        Tone
                      </label>
                      <select
                        id="tone"
                        value={tone}
                        onChange={(e) => setTone(e.target.value as any)}
                        disabled={isGenerating || !activeCV}
                        className="w-full px-4 py-2 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                      >
                        <option value="professional">Professional</option>
                        <option value="confident">Confident</option>
                        <option value="friendly">Friendly</option>
                        <option value="enthusiastic">Enthusiastic</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="coverLetterLength" className="block text-sm font-medium text-neutral-700 mb-2">
                        Cover Letter Length
                      </label>
                      <select
                        id="coverLetterLength"
                        value={coverLetterLength}
                        onChange={(e) => setCoverLetterLength(e.target.value as any)}
                        disabled={isGenerating || !activeCV}
                        className="w-full px-4 py-2 border-2 border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                      >
                        <option value="short">Short (3 paragraphs)</option>
                        <option value="medium">Medium (4 paragraphs)</option>
                        <option value="long">Long (5 paragraphs)</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons - PROMINENT */}
              <div className="mt-8 space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <button
                    type="button"
                    onClick={handleGenerateCV}
                    disabled={isGenerating || !activeCV}
                    className="flex items-center justify-center space-x-2 px-6 py-4 bg-primary-600 text-white rounded-xl hover:bg-primary-700 font-semibold text-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
                  >
                    {generatingCV ? (
                      <>
                        <Loader className="h-5 w-5 animate-spin" />
                        <span>Generating...</span>
                      </>
                    ) : (
                      <>
                        <FileText className="h-5 w-5" />
                        <span>Generate CV</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleGenerateCoverLetter}
                    disabled={isGenerating || !activeCV}
                    className="flex items-center justify-center space-x-2 px-6 py-4 bg-green-600 text-white rounded-xl hover:bg-green-700 font-semibold text-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
                  >
                    {generatingCoverLetter ? (
                      <>
                        <Loader className="h-5 w-5 animate-spin" />
                        <span>Generating...</span>
                      </>
                    ) : (
                      <>
                        <Mail className="h-5 w-5" />
                        <span>Generate Letter</span>
                      </>
                    )}
                  </button>
                </div>

                {(downloadUrl || coverLetterText) && (
                  <button
                    type="button"
                    onClick={handleReset}
                    className="w-full px-4 py-2 text-sm text-neutral-600 hover:text-neutral-800"
                  >
                    Clear & Start New
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* CV Success - CLEAN */}
          {downloadUrl && (
            <div className="bg-green-50 border-2 border-green-200 rounded-2xl p-6 mb-6">
              <div className="flex items-start space-x-4">
                <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-green-900 mb-2">
                    ✅ Your Tailored CV is Ready!
                  </h3>
                  <p className="text-sm text-green-700 mb-4">
                    Download your customized CV below
                  </p>
                  <a
                    href={downloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center space-x-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-semibold"
                  >
                    <FileText className="h-5 w-5" />
                    <span>Download CV</span>
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Cover Letter Success - CLEAN */}
          {coverLetterText && (
            <div className="bg-blue-50 border-2 border-blue-200 rounded-2xl p-6">
              <div className="flex items-start space-x-4 mb-4">
                <Mail className="h-6 w-6 text-blue-600 flex-shrink-0 mt-1" />
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-blue-900 mb-2">
                    ✅ Your Cover Letter is Ready!
                  </h3>
                </div>
              </div>
              
              <div className="bg-white border border-blue-200 rounded-xl p-6 mb-4 max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-800 leading-relaxed">
                  {coverLetterText}
                </pre>
              </div>
              
              <button
                onClick={copyCoverLetterToClipboard}
                className="inline-flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold"
              >
                <Mail className="h-5 w-5" />
                <span>Copy to Clipboard</span>
              </button>
            </div>
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
