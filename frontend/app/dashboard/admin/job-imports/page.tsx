'use client'
import { getUserErrorMessage } from '@/lib/errors'

import { useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  FileUp,
  Loader,
  LogOut,
  ShieldCheck,
  Upload,
  Users,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import {
  commitAlxDigest,
  previewAlxDigest,
  type AlxDigestEntry,
  type AlxDigestPreview,
  type AlxEntryStatus,
  type AlxImportResult,
} from '@/lib/api/admin'
import { signOut } from '@/lib/auth'

const STATUS_META: Record<AlxEntryStatus, { label: string; className: string }> = {
  new: { label: 'New', className: 'bg-emerald-50 text-emerald-700' },
  already_imported: { label: 'Already imported', className: 'bg-neutral-100 text-neutral-600' },
  duplicate_of_scraped: { label: 'Already scraped', className: 'bg-amber-50 text-amber-700' },
}

function getErrorMessage(error: unknown, fallback: string) {
  return getUserErrorMessage(error, fallback)
}

function formatDeadline(value: string | null) {
  if (!value) return 'No deadline'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 'No deadline'
  return parsed.toLocaleDateString([], { dateStyle: 'medium' })
}

function isExpired(value: string | null) {
  if (!value) return false
  const parsed = new Date(value)
  return !Number.isNaN(parsed.getTime()) && parsed.getTime() < Date.now()
}

export default function AdminJobImportsPage() {
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<AlxDigestPreview | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [enrich, setEnrich] = useState(true)
  const [parsing, setParsing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState<AlxImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const entries = preview?.entries ?? []

  const selectedEntries = useMemo(
    () => entries.filter((entry) => selected.has(entry.origin_job_id)),
    [entries, selected]
  )

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const chosen = event.target.files?.[0] ?? null
    setFile(chosen)
    setPreview(null)
    setSelected(new Set())
    setResult(null)
    setError(null)
  }

  const handlePreview = async () => {
    if (!file) return
    setParsing(true)
    setError(null)
    setResult(null)
    try {
      const response = await previewAlxDigest(file)
      setPreview(response)
      // Pre-select only entries that are not already in the job board.
      setSelected(
        new Set(
          response.entries
            .filter((entry) => entry.status === 'new' && !isExpired(entry.deadline))
            .map((entry) => entry.origin_job_id)
        )
      )
    } catch (err) {
      setError(getErrorMessage(err, 'Could not read this digest.'))
    } finally {
      setParsing(false)
    }
  }

  const handleImport = async () => {
    if (selectedEntries.length === 0) return
    setImporting(true)
    setError(null)
    try {
      const response = await commitAlxDigest(selectedEntries, enrich)
      setResult(response)
      setPreview(null)
      setSelected(new Set())
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setError(getErrorMessage(err, 'The import failed.'))
    } finally {
      setImporting(false)
    }
  }

  const toggle = (entry: AlxDigestEntry) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(entry.origin_job_id)) next.delete(entry.origin_job_id)
      else next.add(entry.origin_job_id)
      return next
    })
  }

  const toggleAll = () => {
    setSelected((prev) =>
      prev.size === entries.length
        ? new Set()
        : new Set(entries.map((entry) => entry.origin_job_id))
    )
  }

  if (authLoading || !user) return <div className="min-h-screen bg-neutral-950" />

  return (
    <div className="min-h-screen bg-[#f6f8f7] text-neutral-900">
      <header className="border-b border-white/10 bg-neutral-950 text-white">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-brand-turquoise-500/15 p-2 text-brand-turquoise-300">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-turquoise-300">
                VeloxaHire Admin
              </p>
              <h1 className="mt-1 text-xl font-semibold">Job imports</h1>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-white/60">
            <span className="hidden sm:inline">{user.email}</span>
            <button
              onClick={() => signOut().then(() => router.replace('/auth/login'))}
              className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-2 text-white hover:bg-white/10"
            >
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-6 lg:px-8">
        <div className="mb-7">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-sm font-medium">
            <button
              onClick={() => router.push('/dashboard/admin')}
              className="inline-flex items-center gap-1.5 text-neutral-500 hover:text-neutral-900"
            >
              <BarChart3 className="h-4 w-4" /> Analytics
            </button>
            <span className="text-neutral-300">/</span>
            <button
              onClick={() => router.push('/dashboard/admin/users')}
              className="inline-flex items-center gap-1.5 text-neutral-500 hover:text-neutral-900"
            >
              <Users className="h-4 w-4" /> Users
            </button>
            <span className="text-neutral-300">/</span>
            <span className="text-neutral-900">Job imports</span>
          </div>
          <p className="text-sm text-neutral-500">
            Upload the weekly ALX Ghana Community digest. Entries are parsed and shown for review
            before anything is written to the job board, and appear under Local Jobs once imported.
          </p>
        </div>

        {error && (
          <div className="mb-5 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <section className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
            <div className="flex items-center gap-2 font-semibold text-emerald-800">
              <CheckCircle2 className="h-5 w-5" /> Import complete
            </div>
            <p className="mt-2 text-sm text-emerald-800">
              {result.stats.created} job{result.stats.created === 1 ? '' : 's'} added,{' '}
              {result.stats.updated} refreshed
              {result.stats.skipped_expired > 0 && `, ${result.stats.skipped_expired} past deadline skipped`}
              {result.stats.enrichment_failed > 0 &&
                `, ${result.stats.enrichment_failed} could not be enriched (saved with the digest summary)`}
              .
            </p>
            {result.stats.errors.length > 0 && (
              <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-red-700">
                <li>Some jobs could not be imported. Review the imported jobs before trying again.</li>
              </ul>
            )}
          </section>
        )}

        <section className="mb-6 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <label className="flex-1">
              <span className="mb-2 block text-sm font-semibold text-neutral-700">
                ALX digest PDF
              </span>
              <div className="flex items-center gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={handleFileChange}
                  className="block w-full text-sm text-neutral-600 file:mr-3 file:rounded-xl file:border-0 file:bg-neutral-900 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-neutral-800"
                />
              </div>
            </label>
            <button
              onClick={() => void handlePreview()}
              disabled={!file || parsing}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {parsing ? <Loader className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
              {parsing ? 'Reading digest…' : 'Parse digest'}
            </button>
          </div>
        </section>

        {preview && (
          <section className="rounded-2xl border border-neutral-200 bg-white shadow-sm">
            <div className="flex flex-col gap-3 border-b border-neutral-100 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-semibold text-neutral-900">
                  {preview.parsed} entr{preview.parsed === 1 ? 'y' : 'ies'} found in{' '}
                  {preview.filename}
                </p>
                <p className="mt-1 text-sm text-neutral-500">
                  {preview.counts.new ?? 0} new · {preview.counts.already_imported ?? 0} already
                  imported · {preview.counts.duplicate_of_scraped ?? 0} already scraped
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <label className="inline-flex items-center gap-2 text-sm text-neutral-600">
                  <input
                    type="checkbox"
                    checked={enrich}
                    onChange={(event) => setEnrich(event.target.checked)}
                    className="h-4 w-4 rounded border-neutral-300"
                  />
                  Fetch full descriptions
                </label>
                <button
                  onClick={() => void handleImport()}
                  disabled={selectedEntries.length === 0 || importing}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-turquoise-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-turquoise-700 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {importing ? (
                    <Loader className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  {importing
                    ? 'Importing…'
                    : `Import ${selectedEntries.length} job${selectedEntries.length === 1 ? '' : 's'}`}
                </button>
              </div>
            </div>

            {enrich && (
              <p className="border-b border-neutral-100 bg-neutral-50 px-5 py-3 text-xs text-neutral-500">
                Each selected apply link is fetched and parsed to build a full listing. This takes
                roughly a second per job; entries whose page cannot be read are still imported using
                the digest summary.
              </p>
            )}

            <div className="hidden border-b border-neutral-100 px-5 py-3 text-xs font-bold uppercase tracking-wide text-neutral-400 lg:grid lg:grid-cols-[40px_minmax(0,1.6fr)_minmax(0,1.2fr)_minmax(140px,0.6fr)_minmax(150px,0.6fr)]">
              <span>
                <input
                  type="checkbox"
                  checked={entries.length > 0 && selected.size === entries.length}
                  onChange={toggleAll}
                  aria-label="Select all entries"
                  className="h-4 w-4 rounded border-neutral-300"
                />
              </span>
              <span>Role</span>
              <span>Company</span>
              <span>Deadline</span>
              <span>Status</span>
            </div>

            {entries.map((entry) => {
              const expired = isExpired(entry.deadline)
              return (
                <div
                  key={entry.origin_job_id}
                  className="grid gap-2 border-b border-neutral-100 px-5 py-4 last:border-0 lg:grid-cols-[40px_minmax(0,1.6fr)_minmax(0,1.2fr)_minmax(140px,0.6fr)_minmax(150px,0.6fr)] lg:items-center lg:gap-4"
                >
                  <div>
                    <input
                      type="checkbox"
                      checked={selected.has(entry.origin_job_id)}
                      onChange={() => toggle(entry)}
                      aria-label={`Select ${entry.title}`}
                      className="h-4 w-4 rounded border-neutral-300"
                    />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-neutral-900">{entry.title}</p>
                    <a
                      href={entry.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-0.5 block truncate text-xs text-brand-turquoise-700 hover:underline"
                    >
                      {entry.apply_url}
                    </a>
                  </div>
                  <div className="min-w-0 truncate text-sm text-neutral-600">{entry.company}</div>
                  <div className={`text-sm ${expired ? 'text-red-600' : 'text-neutral-600'}`}>
                    {formatDeadline(entry.deadline)}
                    {expired && ' (passed)'}
                  </div>
                  <div>
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_META[entry.status].className}`}
                    >
                      {STATUS_META[entry.status].label}
                    </span>
                  </div>
                </div>
              )
            })}
          </section>
        )}
      </main>
    </div>
  )
}
