'use client'

import { useEffect, useRef, useState } from 'react'
import {
  FileText,
  Upload,
  Download,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle,
  Clock,
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import {
  uploadCV,
  getActiveCV,
  deleteCV,
  getCVDownloadURL,
  type CVDetail,
} from '@/lib/api/cvs'

const ALLOWED_EXTENSIONS = ['.pdf', '.docx']
const MAX_BYTES = 10 * 1024 * 1024 // 10 MB

function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function validateFile(file: File): string | null {
  const ext = '.' + (file.name.split('.').pop()?.toLowerCase() ?? '')
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return 'Only PDF and DOCX files are supported.'
  }
  if (file.size > MAX_BYTES) {
    return 'File too large. Max size is 10 MB.'
  }
  return null
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-md px-1.5 py-0.5">
          <CheckCircle2 className="w-3 h-3" />
          Parsed
        </span>
      )
    case 'processing':
    case 'pending':
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-neutral-600 bg-neutral-50 border border-neutral-200 rounded-md px-1.5 py-0.5">
          <Clock className="w-3 h-3" />
          Processing
        </span>
      )
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-700 bg-rose-50 border border-rose-100 rounded-md px-1.5 py-0.5">
          <XCircle className="w-3 h-3" />
          Failed
        </span>
      )
    default:
      return null
  }
}

export function CVSection() {
  const [cv, setCV] = useState<CVDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    load()
  }, [])

  const load = async () => {
    try {
      setLoading(true)
      setCV(await getActiveCV())
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleFiles = async (file: File) => {
    const error = validateFile(file)
    if (error) {
      toast.error(error)
      return
    }
    try {
      setUploading(true)
      await uploadCV(file)
      toast.success('CV uploaded — parsing in progress')
      await load()
    } catch (err: any) {
      console.error(err)
      toast.error(err?.response?.data?.detail || 'Failed to upload CV')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async () => {
    if (!cv) return
    if (!confirm('Delete this CV? You can upload a new one at any time.')) return
    try {
      await deleteCV(cv.id)
      toast.success('CV removed')
      setCV(null)
    } catch (err: any) {
      console.error(err)
      toast.error(err?.response?.data?.detail || 'Failed to delete CV')
    }
  }

  const handleDownload = async () => {
    if (!cv) return
    try {
      const { download_url } = await getCVDownloadURL(cv.id)
      window.open(download_url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      console.error(err)
      toast.error('Could not generate download link')
    }
  }

  return (
    <section className="bg-white rounded-xl border border-neutral-200 p-5">
      <header className="flex items-center gap-2 mb-1">
        <FileText className="w-4 h-4 text-neutral-600" />
        <h2 className="text-sm font-semibold text-neutral-900">CV</h2>
      </header>
      <p className="text-xs text-neutral-500 mb-4">
        We use your CV to improve job matches. Only the parsed skills and experience are used for ranking.
      </p>

      {loading ? (
        <div className="flex items-center justify-center py-6 text-neutral-400">
          <Loader2 className="w-4 h-4 animate-spin" />
        </div>
      ) : cv ? (
        <ActiveCVCard
          cv={cv}
          uploading={uploading}
          onReplace={() => inputRef.current?.click()}
          onDelete={handleDelete}
          onDownload={handleDownload}
        />
      ) : (
        <UploadDropzone
          dragActive={dragActive}
          uploading={uploading}
          onDrop={(e) => {
            e.preventDefault()
            setDragActive(false)
            const file = e.dataTransfer.files[0]
            if (file) handleFiles(file)
          }}
          onDragOver={(e) => {
            e.preventDefault()
            setDragActive(true)
          }}
          onDragLeave={(e) => {
            e.preventDefault()
            setDragActive(false)
          }}
          onChoose={() => inputRef.current?.click()}
        />
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFiles(file)
          e.target.value = ''
        }}
      />
    </section>
  )
}

function ActiveCVCard({
  cv,
  uploading,
  onReplace,
  onDelete,
  onDownload,
}: {
  cv: CVDetail
  uploading: boolean
  onReplace: () => void
  onDelete: () => void
  onDownload: () => void
}) {
  return (
    <div className="rounded-lg border border-neutral-200 p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0 flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-neutral-50 flex items-center justify-center flex-shrink-0">
            <FileText className="w-4 h-4 text-neutral-600" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-neutral-900 truncate">
              {cv.file_name}
            </p>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500 mt-0.5">
              {cv.file_size != null && <span>{formatFileSize(cv.file_size)}</span>}
              {cv.file_type && <span className="uppercase">{cv.file_type}</span>}
              <span>{new Date(cv.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>
        <StatusBadge status={cv.parsing_status} />
      </div>

      {cv.parsing_status === 'failed' && cv.parsing_error && (
        <div className="mb-3 flex items-start gap-2 p-2 bg-rose-50 border border-rose-100 rounded-md text-xs text-rose-700">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>{cv.parsing_error}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={onReplace}
          disabled={uploading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-neutral-200 hover:border-neutral-300 text-neutral-700 rounded-lg text-xs font-medium disabled:opacity-50 transition-colors"
        >
          {uploading ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Uploading…
            </>
          ) : (
            <>
              <Upload className="w-3.5 h-3.5" />
              Replace
            </>
          )}
        </button>
        <button
          onClick={onDownload}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-neutral-200 hover:border-neutral-300 text-neutral-700 rounded-lg text-xs font-medium transition-colors"
        >
          <Download className="w-3.5 h-3.5" />
          Download
        </button>
        <button
          onClick={onDelete}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-neutral-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg text-xs font-medium transition-colors ml-auto"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Remove
        </button>
      </div>
    </div>
  )
}

function UploadDropzone({
  dragActive,
  uploading,
  onDrop,
  onDragOver,
  onDragLeave,
  onChoose,
}: {
  dragActive: boolean
  uploading: boolean
  onDrop: (e: React.DragEvent) => void
  onDragOver: (e: React.DragEvent) => void
  onDragLeave: (e: React.DragEvent) => void
  onChoose: () => void
}) {
  return (
    <div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      className={`rounded-lg border border-dashed p-6 text-center transition-colors ${
        dragActive
          ? 'border-brand-turquoise-400 bg-brand-turquoise-50/40'
          : 'border-neutral-200 bg-neutral-50/40'
      }`}
    >
      <div className="w-10 h-10 rounded-lg bg-white border border-neutral-200 flex items-center justify-center mx-auto mb-3">
        <Upload className="w-4 h-4 text-neutral-500" />
      </div>
      <p className="text-sm font-medium text-neutral-900 mb-1">Upload your CV</p>
      <p className="text-xs text-neutral-500 mb-3">
        PDF or DOCX, up to 10 MB. Drop a file or browse.
      </p>
      <button
        type="button"
        onClick={onChoose}
        disabled={uploading}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-xs font-medium disabled:opacity-50 transition-colors"
      >
        {uploading ? (
          <>
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Uploading…
          </>
        ) : (
          <>
            <Upload className="w-3.5 h-3.5" />
            Choose file
          </>
        )}
      </button>
      <p className="text-[11px] text-neutral-400 mt-3">
        DOCX preserves original formatting. Either format works for matching.
      </p>
    </div>
  )
}
