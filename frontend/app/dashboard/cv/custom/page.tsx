'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { generateCustomTailoredCV, generateCustomCoverLetter, GenerateCustomCVRequest, GenerateCoverLetterRequest } from '@/lib/api/applications'
import { getActiveCV, CVDetail } from '@/lib/api/cvs'
import { FileText, Sparkles, AlertCircle, Loader, CheckCircle, ArrowLeft, Mail } from 'lucide-react'
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
  
  // Form state
  const [jobTitle, setJobTitle] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [location, setLocation] = useState('')
  const [jobType, setJobType] = useState('full-time')
  const [remoteType, setRemoteType] = useState('unspecified')
  const [tone, setTone] = useState<'professional' | 'confident' | 'friendly' | 'enthusiastic'>('professional')
  const [highlightSkills, setHighlightSkills] = useState(true)
  const [emphasizeExperience, setEmphasizeExperience] = useState(true)
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

  const handleGenerateCV = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!activeCV) {
      toast.error('Please upload a CV before generating tailored versions')
      return
    }

    if (activeCV.parsing_status !== 'completed') {
      toast.error('Please wait for your CV to finish parsing')
      return
    }

    // Validate required fields
    if (!jobTitle.trim()) {
      toast.error('Job title is required')
      return
    }
    if (!companyName.trim()) {
      toast.error('Company name is required')
      return
    }
    if (!jobDescription.trim()) {
      toast.error('Job description is required')
      return
    }

    try {
      setGeneratingCV(true)
      setDownloadUrl(null)

      const request: GenerateCustomCVRequest = {
        job_title: jobTitle.trim(),
        company_name: companyName.trim(),
        job_description: jobDescription.trim(),
        location: location.trim() || undefined,
        job_type: jobType,
        remote_type: remoteType,
        tone,
        highlight_skills: highlightSkills,
        emphasize_relevant_experience: emphasizeExperience,
      }

      const result = await generateCustomTailoredCV(request)

      toast.success('Tailored CV generated successfully!')
      
      // Set download URL if available
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

  const handleGenerateCoverLetter = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!activeCV) {
      toast.error('Please upload a CV before generating cover letters')
      return
    }

    if (activeCV.parsing_status !== 'completed') {
      toast.error('Please wait for your CV to finish parsing')
      return
    }

    // Validate required fields
    if (!jobTitle.trim()) {
      toast.error('Job title is required')
      return
    }
    if (!companyName.trim()) {
      toast.error('Company name is required')
      return
    }
    if (!jobDescription.trim()) {
      toast.error('Job description is required')
      return
    }

    try {
      setGeneratingCoverLetter(true)
      setCoverLetterText(null)

      const request: GenerateCoverLetterRequest = {
        job_title: jobTitle.trim(),
        company_name: companyName.trim(),
        job_description: jobDescription.trim(),
        location: location.trim() || undefined,
        job_type: jobType,
        remote_type: remoteType,
        tone,
        length: coverLetterLength,
      }

      const result = await generateCustomCoverLetter(request)

      toast.success('Cover letter generated successfully!')
      
      // Set cover letter text
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
    setJobTitle('')
    setCompanyName('')
    setJobDescription('')
    setLocation('')
    setJobType('full-time')
    setRemoteType('unspecified')
    setTone('professional')
    setHighlightSkills(true)
    setEmphasizeExperience(true)
    setCoverLetterLength('medium')
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
        <div className="max-w-4xl mx-auto">
          {/* Back button */}
          <Link 
            href="/dashboard/cv"
            className="inline-flex items-center space-x-2 text-neutral-600 hover:text-neutral-800 mb-6 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to CV Management</span>
          </Link>

          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center space-x-3 mb-2">
              <Sparkles className="h-8 w-8 text-primary-600" />
              <h1 className="text-3xl font-bold text-neutral-800">Generate Custom CV & Cover Letter</h1>
            </div>
            <p className="text-neutral-600">
              Paste any job description and generate a tailored CV and/or cover letter instantly
            </p>
          </div>

          {/* CV Status Card */}
          {activeCV ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
              <div className="flex items-start space-x-3">
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-900">
                    Active CV: {activeCV.file_name}
                  </p>
                  <p className="text-xs text-green-700 mt-1">
                    Your CV is ready. Fill in the job details below to generate a tailored version.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
              <div className="flex items-start space-x-3">
                <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-yellow-900">No Active CV Found</p>
                  <p className="text-xs text-yellow-700 mt-1">
                    Please{' '}
                    <Link href="/dashboard/cv" className="underline font-medium">
                      upload a CV
                    </Link>{' '}
                    before generating tailored versions.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Generation Form */}
          <form onSubmit={(e) => e.preventDefault()} className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
            <h2 className="text-lg font-semibold text-neutral-800 mb-4">Job Details</h2>

            {/* Job Title */}
            <div className="mb-4">
              <label htmlFor="jobTitle" className="block text-sm font-medium text-neutral-700 mb-2">
                Job Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="jobTitle"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g., Senior Software Engineer"
                disabled={isGenerating || !activeCV}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
                required
              />
            </div>

            {/* Company Name */}
            <div className="mb-4">
              <label htmlFor="companyName" className="block text-sm font-medium text-neutral-700 mb-2">
                Company Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="companyName"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g., Tech Corp"
                disabled={isGenerating || !activeCV}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
                required
              />
            </div>

            {/* Job Description */}
            <div className="mb-4">
              <label htmlFor="jobDescription" className="block text-sm font-medium text-neutral-700 mb-2">
                Job Description <span className="text-red-500">*</span>
              </label>
              <textarea
                id="jobDescription"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job description here, including responsibilities, requirements, qualifications, etc."
                disabled={isGenerating || !activeCV}
                rows={12}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50 resize-y"
                required
              />
              <p className="text-xs text-neutral-500 mt-1">
                The more detailed the job description, the better we can tailor your CV
              </p>
            </div>

            {/* Optional Fields Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {/* Location */}
              <div>
                <label htmlFor="location" className="block text-sm font-medium text-neutral-700 mb-2">
                  Location
                </label>
                <input
                  type="text"
                  id="location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g., San Francisco, CA"
                  disabled={isGenerating || !activeCV}
                  className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
                />
              </div>

              {/* Job Type */}
              <div>
                <label htmlFor="jobType" className="block text-sm font-medium text-neutral-700 mb-2">
                  Job Type
                </label>
                <select
                  id="jobType"
                  value={jobType}
                  onChange={(e) => setJobType(e.target.value)}
                  disabled={isGenerating || !activeCV}
                  className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
                >
                  <option value="full-time">Full-time</option>
                  <option value="part-time">Part-time</option>
                  <option value="contract">Contract</option>
                  <option value="internship">Internship</option>
                </select>
              </div>

              {/* Remote Type */}
              <div>
                <label htmlFor="remoteType" className="block text-sm font-medium text-neutral-700 mb-2">
                  Remote Type
                </label>
                <select
                  id="remoteType"
                  value={remoteType}
                  onChange={(e) => setRemoteType(e.target.value)}
                  disabled={isGenerating || !activeCV}
                  className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
                >
                  <option value="unspecified">Unspecified</option>
                  <option value="remote">Remote</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="on-site">On-site</option>
                </select>
              </div>
            </div>

            <hr className="my-6" />

            {/* Customization Options */}
            <h2 className="text-lg font-semibold text-neutral-800 mb-4">Customization Options</h2>

            {/* Tone */}
            <div className="mb-4">
              <label htmlFor="tone" className="block text-sm font-medium text-neutral-700 mb-2">
                Tone
              </label>
              <select
                id="tone"
                value={tone}
                onChange={(e) => setTone(e.target.value as any)}
                disabled={isGenerating || !activeCV}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
              >
                <option value="professional">Professional</option>
                <option value="confident">Confident</option>
                <option value="friendly">Friendly</option>
                <option value="enthusiastic">Enthusiastic</option>
              </select>
            </div>

            {/* Cover Letter Length */}
            <div className="mb-4">
              <label htmlFor="coverLetterLength" className="block text-sm font-medium text-neutral-700 mb-2">
                Cover Letter Length
              </label>
              <select
                id="coverLetterLength"
                value={coverLetterLength}
                onChange={(e) => setCoverLetterLength(e.target.value as 'short' | 'medium' | 'long')}
                disabled={isGenerating || !activeCV}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
              >
                <option value="short">Short (3 paragraphs)</option>
                <option value="medium">Medium (4 paragraphs)</option>
                <option value="long">Long (5 paragraphs)</option>
              </select>
              <p className="text-xs text-neutral-500 mt-1">
                Applies to cover letter generation
              </p>
            </div>

            {/* Checkboxes */}
            <div className="space-y-3 mb-6">
              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={highlightSkills}
                  onChange={(e) => setHighlightSkills(e.target.checked)}
                  disabled={isGenerating || !activeCV}
                  className="mt-1 h-4 w-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500 disabled:opacity-50"
                />
                <div>
                  <span className="text-sm font-medium text-neutral-700">Highlight Relevant Skills</span>
                  <p className="text-xs text-neutral-500">Emphasize skills that match the job requirements</p>
                </div>
              </label>

              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={emphasizeExperience}
                  onChange={(e) => setEmphasizeExperience(e.target.checked)}
                  disabled={isGenerating || !activeCV}
                  className="mt-1 h-4 w-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500 disabled:opacity-50"
                />
                <div>
                  <span className="text-sm font-medium text-neutral-700">Emphasize Relevant Experience</span>
                  <p className="text-xs text-neutral-500">Highlight work experience related to this position</p>
                </div>
              </label>
            </div>

            {/* Action Buttons */}
            <div className="pt-6 border-t border-neutral-200">
              <div className="flex items-center justify-between mb-4">
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={isGenerating || !activeCV}
                  className="px-6 py-2 text-sm font-medium text-neutral-700 hover:text-neutral-900 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Clear Form
                </button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Generate CV Button */}
                <button
                  type="button"
                  onClick={handleGenerateCV}
                  disabled={isGenerating || !activeCV}
                  className="flex items-center justify-center space-x-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generatingCV ? (
                    <>
                      <Loader className="h-5 w-5 animate-spin" />
                      <span>Generating CV...</span>
                    </>
                  ) : (
                    <>
                      <FileText className="h-5 w-5" />
                      <span>Generate Tailored CV</span>
                    </>
                  )}
                </button>

                {/* Generate Cover Letter Button */}
                <button
                  type="button"
                  onClick={handleGenerateCoverLetter}
                  disabled={isGenerating || !activeCV}
                  className="flex items-center justify-center space-x-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generatingCoverLetter ? (
                    <>
                      <Loader className="h-5 w-5 animate-spin" />
                      <span>Generating Letter...</span>
                    </>
                  ) : (
                    <>
                      <Mail className="h-5 w-5" />
                      <span>Generate Cover Letter</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>

          {/* Success Message with Download */}
          {downloadUrl && (
            <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-6">
              <div className="flex items-start space-x-3">
                <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-green-900 mb-2">
                    Your Tailored CV is Ready!
                  </h3>
                  <p className="text-sm text-green-700 mb-4">
                    Your CV has been customized for {jobTitle} at {companyName}. Download it below.
                  </p>
                  <div className="flex items-center space-x-3">
                    <a
                      href={downloadUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                    >
                      <FileText className="h-4 w-4" />
                      <span>Download CV</span>
                    </a>
                    <button
                      onClick={handleReset}
                      className="px-4 py-2 text-sm text-green-700 hover:text-green-900"
                    >
                      Generate Another
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Cover Letter Display */}
          {coverLetterText && (
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
              <div className="flex items-start space-x-3 mb-4">
                <Mail className="h-6 w-6 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-blue-900 mb-2">
                    Your Cover Letter is Ready!
                  </h3>
                  <p className="text-sm text-blue-700 mb-4">
                    Your cover letter has been generated for {jobTitle} at {companyName}.
                  </p>
                </div>
              </div>
              
              {/* Cover Letter Text Box */}
              <div className="bg-white border border-blue-200 rounded-lg p-4 mb-4">
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-800">
                    {coverLetterText}
                  </pre>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex items-center space-x-3">
                <button
                  onClick={copyCoverLetterToClipboard}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <Mail className="h-4 w-4" />
                  <span>Copy to Clipboard</span>
                </button>
                <button
                  onClick={handleReset}
                  className="px-4 py-2 text-sm text-blue-700 hover:text-blue-900"
                >
                  Generate Another
                </button>
              </div>
            </div>
          )}

          {/* Info Box */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-blue-900 mb-1">How it works</p>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>• Paste any job description from any source (LinkedIn, Indeed, company websites, etc.)</li>
                  <li>• <strong>Generate CV:</strong> Our AI tailors your CV to highlight relevant experience and skills</li>
                  <li>• <strong>Generate Cover Letter:</strong> Our AI writes a personalized cover letter for the position</li>
                  <li>• Your original CV remains unchanged - we create new customized versions</li>
                  <li>• Generated CVs maintain your original formatting (DOCX) or create a professional new format</li>
                  <li>• Cover letters are formatted and ready to copy or customize further</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
