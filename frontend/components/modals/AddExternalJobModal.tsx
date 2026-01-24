'use client'

import { useState } from 'react'
import { X, Link as LinkIcon, FileText, Loader2, CheckCircle2, AlertCircle, Sparkles, ArrowRight, Zap } from 'lucide-react'
import { addJobFromURL, addJobFromText } from '@/lib/api/external-jobs'
import { toast } from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'

interface AddExternalJobModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

type TabType = 'url' | 'text'
type Status = 'idle' | 'loading' | 'success' | 'error'

export function AddExternalJobModal({ isOpen, onClose, onSuccess }: AddExternalJobModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('url')
  const [url, setUrl] = useState('')
  const [text, setText] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [resultMessage, setResultMessage] = useState('')
  const [createdJobId, setCreatedJobId] = useState<string | null>(null)

  const handleReset = () => {
    setUrl('')
    setText('')
    setSourceUrl('')
    setStatus('idle')
    setResultMessage('')
    setCreatedJobId(null)
  }

  const handleClose = () => {
    handleReset()
    onClose()
  }

  const handleSubmitURL = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!url.trim()) {
      toast.error('Please enter a job URL')
      return
    }

    setStatus('loading')
    
    try {
      const response = await addJobFromURL(url)
      setStatus('success')
      setResultMessage(`"${response.title}" at ${response.company} has been added!`)
      setCreatedJobId(response.id)
      toast.success('Job added successfully!')
      
      onSuccess?.()
      
    } catch (error: any) {
      setStatus('error')
      setResultMessage(error.message || 'Failed to add job. Please try again.')
      toast.error(error.message || 'Failed to add job')
    }
  }

  const handleSubmitText = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!text.trim()) {
      toast.error('Please paste the job description')
      return
    }

    if (text.length < 50) {
      toast.error('Job description is too short. Please provide more details.')
      return
    }

    setStatus('loading')
    
    try {
      const response = await addJobFromText(text, sourceUrl || undefined)
      setStatus('success')
      setResultMessage(`"${response.title}" at ${response.company} has been added!`)
      setCreatedJobId(response.id)
      toast.success('Job added successfully!')
      
      onSuccess?.()
      
    } catch (error: any) {
      setStatus('error')
      setResultMessage(error.message || 'Failed to add job. Please try again.')
      toast.error(error.message || 'Failed to add job')
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleClose}
          className="absolute inset-0 bg-neutral-900/60 backdrop-blur-sm"
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-brand-turquoise-600 to-brand-turquoise-500 px-8 py-6 relative overflow-hidden">
            <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10"></div>
            <div className="relative flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-black text-white mb-1">Add External Job</h2>
                <p className="text-brand-turquoise-100 text-sm">Paste a job URL or description to add it to your list</p>
              </div>
              <button
                onClick={handleClose}
                className="p-2 hover:bg-white/20 rounded-full transition-colors"
              >
                <X className="w-6 h-6 text-white" />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-neutral-100 px-8 pt-6">
            <button
              onClick={() => setActiveTab('url')}
              className={`flex items-center space-x-2 px-6 py-3 font-bold text-sm rounded-t-xl transition-all ${
                activeTab === 'url'
                  ? 'bg-white text-brand-turquoise-600 border-t border-x border-neutral-100 -mb-px'
                  : 'text-neutral-400 hover:text-brand-turquoise-600'
              }`}
            >
              <LinkIcon className="w-4 h-4" />
              <span>From URL</span>
            </button>
            <button
              onClick={() => setActiveTab('text')}
              className={`flex items-center space-x-2 px-6 py-3 font-bold text-sm rounded-t-xl transition-all ${
                activeTab === 'text'
                  ? 'bg-white text-brand-turquoise-600 border-t border-x border-neutral-100 -mb-px'
                  : 'text-neutral-400 hover:text-brand-turquoise-600'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>From Text</span>
            </button>
          </div>

          {/* Content */}
          <div className="p-8">
            {status === 'success' ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center py-8"
              >
                <div className="w-20 h-20 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-6">
                  <CheckCircle2 className="w-10 h-10 text-green-500" />
                </div>
                <h3 className="text-2xl font-black text-neutral-900 mb-2">Job Added Successfully!</h3>
                <p className="text-neutral-500 mb-8 max-w-sm mx-auto">{resultMessage}</p>
                
                <div className="space-y-4">
                  <Link
                    href={`/dashboard/applications/generate/${createdJobId}`}
                    onClick={handleClose}
                    className="flex items-center justify-center space-x-3 w-full btn-premium py-5 bg-gradient-to-r from-brand-orange-500 to-brand-orange-600 text-white rounded-2xl font-black text-lg shadow-xl shadow-brand-orange-500/20 group"
                  >
                    <Zap className="w-6 h-6 fill-white" />
                    <span>Generate Tailored CV & Cover Letter Now</span>
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </Link>
                  
                  <div className="flex gap-4">
                    <button
                      onClick={handleClose}
                      className="flex-1 py-4 px-6 bg-neutral-100 text-neutral-600 rounded-2xl font-bold hover:bg-neutral-200 transition-colors"
                    >
                      Add Another Job
                    </button>
                    <Link
                      href="/dashboard/jobs"
                      onClick={handleClose}
                      className="flex-1 py-4 px-6 bg-brand-turquoise-50 text-brand-turquoise-600 rounded-2xl font-bold hover:bg-brand-turquoise-100 transition-colors text-center"
                    >
                      Browse All Jobs
                    </Link>
                  </div>
                </div>

                <div className="mt-10 p-4 bg-brand-turquoise-50 rounded-2xl border border-brand-turquoise-100 flex items-center gap-3 text-left">
                  <Sparkles className="w-5 h-5 text-brand-turquoise-600 flex-shrink-0" />
                  <p className="text-sm text-brand-turquoise-800 font-medium leading-tight">
                    <strong>Pro Tip:</strong> You can always find this job in <strong>Applications → Saved Jobs</strong> to generate materials later.
                  </p>
                </div>
              </motion.div>
            ) : (
              <>
                {status === 'error' && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6 p-6 bg-red-50 border border-red-200 rounded-2xl flex items-start space-x-4"
                  >
                    <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-red-900 mb-1">Error</p>
                      <p className="text-red-700 text-sm">{resultMessage}</p>
                      {activeTab === 'url' && (
                        <button
                          type="button"
                          onClick={() => { setActiveTab('text'); setStatus('idle'); setResultMessage(''); }}
                          className="mt-2 text-sm font-bold text-brand-turquoise-600 hover:text-brand-turquoise-700 underline"
                        >
                          Try pasting the job text instead →
                        </button>
                      )}
                    </div>
                  </motion.div>
                )}

                {activeTab === 'url' && (
                  <form onSubmit={handleSubmitURL} className="space-y-6">
                    <div>
                      <label className="block text-xs font-black text-neutral-400 uppercase tracking-widest mb-2">
                        Job Posting URL
                      </label>
                      <div className="relative">
                        <input
                          type="url"
                          value={url}
                          onChange={(e) => setUrl(e.target.value)}
                          placeholder="https://company.com/careers/senior-developer"
                          disabled={status === 'loading'}
                          className="w-full pl-12 pr-4 py-4 bg-neutral-50 border border-neutral-100 rounded-2xl focus:ring-2 focus:ring-brand-turquoise-500 focus:bg-white transition-all outline-none text-neutral-900 font-medium disabled:opacity-50"
                        />
                        <LinkIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                      </div>
                      {url && (() => {
                        try {
                          const domain = new URL(url).hostname.toLowerCase()
                          return (domain.includes('linkedin.com') || domain.includes('indeed.com') || domain.includes('glassdoor.com'))
                        } catch { return false }
                      })() && (
                        <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                          <p className="text-xs font-bold text-amber-800 mb-1">⚠️ This site requires login</p>
                          <p className="text-xs text-amber-700 leading-relaxed">
                            LinkedIn, Indeed, and Glassdoor block direct access. Click <strong>"From Text"</strong> above and paste the full job description instead.
                          </p>
                        </div>
                      )}
                      {!url && (
                        <p className="mt-2 text-xs text-neutral-400">
                          Paste any job posting URL — we'll extract the details automatically using AI.
                        </p>
                      )}
                    </div>

                    <button
                      type="submit"
                      disabled={status === 'loading'}
                      className="w-full btn-premium px-6 py-4 bg-brand-turquoise-600 text-white rounded-2xl font-black text-lg shadow-xl shadow-brand-turquoise-500/20 disabled:opacity-50 flex items-center justify-center space-x-3"
                    >
                      {status === 'loading' ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          <span>Extracting Job Details...</span>
                        </>
                      ) : (
                        <span>Add Job from URL</span>
                      )}
                    </button>
                  </form>
                )}

                {activeTab === 'text' && (
                  <form onSubmit={handleSubmitText} className="space-y-6">
                    <div>
                      <label className="block text-xs font-black text-neutral-400 uppercase tracking-widest mb-2">
                        Job Description
                      </label>
                      <div className="mb-3 p-3 bg-brand-turquoise-50 border border-brand-turquoise-200 rounded-xl">
                        <p className="text-xs font-bold text-brand-turquoise-800 mb-1">💡 Best for LinkedIn Jobs</p>
                        <p className="text-xs text-brand-turquoise-700 leading-relaxed">
                          Open the job posting in your browser, select all text (Ctrl+A), copy, and paste here.
                        </p>
                      </div>
                      <div className="relative">
                        <textarea
                          value={text}
                          onChange={(e) => setText(e.target.value)}
                          placeholder="Paste the entire job posting here..."
                          rows={8}
                          disabled={status === 'loading'}
                          className="w-full pl-12 pr-4 py-4 bg-neutral-50 border border-neutral-100 rounded-2xl focus:ring-2 focus:ring-brand-turquoise-500 focus:bg-white transition-all outline-none text-neutral-900 font-medium resize-none disabled:opacity-50"
                        />
                        <FileText className="absolute left-4 top-4 w-5 h-5 text-neutral-400" />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-black text-neutral-400 uppercase tracking-widest mb-2">
                        Source URL (Optional)
                      </label>
                      <input
                        type="url"
                        value={sourceUrl}
                        onChange={(e) => setSourceUrl(e.target.value)}
                        placeholder="https://linkedin.com/jobs/view/..."
                        disabled={status === 'loading'}
                        className="w-full px-4 py-4 bg-neutral-50 border border-neutral-100 rounded-2xl focus:ring-2 focus:ring-brand-turquoise-500 focus:bg-white transition-all outline-none text-neutral-900 font-medium disabled:opacity-50"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={status === 'loading'}
                      className="w-full btn-premium px-6 py-4 bg-brand-turquoise-600 text-white rounded-2xl font-black text-lg shadow-xl shadow-brand-turquoise-500/20 disabled:opacity-50 flex items-center justify-center space-x-3"
                    >
                      {status === 'loading' ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          <span>Parsing Job Details...</span>
                        </>
                      ) : (
                        <span>Add Job from Text</span>
                      )}
                    </button>
                  </form>
                )}
              </>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
