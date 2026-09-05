'use client'

import { useCallback, useDeferredValue, useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Download, History, Plus, Printer, RotateCcw, Save, Trash2, Undo2 } from 'lucide-react'
import toast from 'react-hot-toast'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import {
  downloadCVGeneration,
  getCVGeneration,
  getCVRevisions,
  resetCVGeneration,
  restoreCVRevision,
  saveCVGeneration,
  type CVContent,
  type CVGeneration,
  type CVRevision,
} from '@/lib/api/cv-generations'

type SaveState = 'saved' | 'saving' | 'unsaved' | 'error'

const inputClass =
  'w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 outline-none focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-100'

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-neutral-600">{label}</span>
      <input className={inputClass} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}

function LinesField({
  label,
  values,
  onChange,
  rows = 4,
}: {
  label: string
  values: string[]
  onChange: (values: string[]) => void
  rows?: number
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-neutral-600">{label}</span>
      <textarea
        className={inputClass}
        rows={rows}
        value={values.join('\n')}
        onChange={(event) => onChange(event.target.value.split('\n'))}
      />
    </label>
  )
}

function CVPreview({ content }: { content: CVContent }) {
  const contact = Object.values(content.personal_info).filter(Boolean)
  return (
    <article id="cv-preview" className="min-h-[1120px] bg-white px-10 py-12 text-[13px] leading-relaxed text-neutral-800 shadow-sm">
      <header className="border-b-2 border-emerald-800 pb-5 text-center">
        <h1 className="text-3xl font-bold text-emerald-900">{content.personal_info.name || 'Your name'}</h1>
        <p className="mt-2 text-xs text-neutral-600">{contact.slice(1).join('  •  ')}</p>
      </header>
      {content.summary && <PreviewSection title="Professional summary"><p>{content.summary}</p></PreviewSection>}
      {(content.skills.technical.length > 0 || content.skills.certifications.length > 0) && (
        <PreviewSection title="Skills">
          {content.skills.technical.filter(Boolean).length > 0 && <p>{content.skills.technical.filter(Boolean).join(', ')}</p>}
          {content.skills.certifications.filter(Boolean).length > 0 && <p className="mt-1"><strong>Certifications:</strong> {content.skills.certifications.filter(Boolean).join(', ')}</p>}
          {content.skills.languages.filter(Boolean).length > 0 && <p className="mt-1"><strong>Languages:</strong> {content.skills.languages.filter(Boolean).join(', ')}</p>}
        </PreviewSection>
      )}
      {content.experience.length > 0 && (
        <PreviewSection title="Experience">
          <div className="space-y-4">
            {content.experience.map((item, index) => (
              <div key={`${item.company}-${index}`}>
                <div className="flex justify-between gap-4 font-semibold text-neutral-900">
                  <span>{item.title}{item.company ? ` | ${item.company}` : ''}</span>
                  <span className="whitespace-nowrap text-xs font-normal">{[item.start_date, item.end_date].filter(Boolean).join(' – ')}</span>
                </div>
                {item.location && <p className="text-xs italic text-neutral-500">{item.location}</p>}
                {item.description && <p className="mt-1">{item.description}</p>}
                {item.achievements.filter(Boolean).length > 0 && <ul className="mt-1 list-disc space-y-0.5 pl-5">{item.achievements.filter(Boolean).map((value, itemIndex) => <li key={itemIndex}>{value}</li>)}</ul>}
              </div>
            ))}
          </div>
        </PreviewSection>
      )}
      {content.education.length > 0 && <PreviewSection title="Education">{content.education.map((item, index) => <div key={index} className="mb-2"><p className="font-semibold text-neutral-900">{item.degree}{item.institution ? ` | ${item.institution}` : ''}</p><p className="text-xs text-neutral-600">{[item.location, item.graduation_date, item.gpa].filter(Boolean).join(' • ')}</p></div>)}</PreviewSection>}
      {content.projects.length > 0 && <PreviewSection title="Projects">{content.projects.map((item, index) => <div key={index} className="mb-2"><p><strong>{item.name}</strong>{item.description ? ` — ${item.description}` : ''}</p>{item.technologies.filter(Boolean).length > 0 && <p className="text-xs text-neutral-500">{item.technologies.filter(Boolean).join(', ')}</p>}</div>)}</PreviewSection>}
    </article>
  )
}

function PreviewSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mt-5"><h2 className="mb-2 border-b border-neutral-200 pb-1 text-xs font-bold uppercase tracking-wider text-emerald-800">{title}</h2>{children}</section>
}

export default function CVEditorPage() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const [generation, setGeneration] = useState<CVGeneration | null>(null)
  const [content, setContent] = useState<CVContent | null>(null)
  const [revisions, setRevisions] = useState<CVRevision[]>([])
  const [saveState, setSaveState] = useState<SaveState>('saved')
  const [loading, setLoading] = useState(true)
  const lastSaved = useRef('')
  const revisionRef = useRef(1)
  const saveQueue = useRef<Promise<void>>(Promise.resolve())
  const previewContent = useDeferredValue(content)

  const load = useCallback(async () => {
    try {
      const [draft, history] = await Promise.all([getCVGeneration(id), getCVRevisions(id)])
      setGeneration(draft)
      setContent(draft.content)
      setRevisions(history)
      revisionRef.current = draft.revision
      lastSaved.current = JSON.stringify(draft.content)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not load this CV.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    if (!content) return
    const serialized = JSON.stringify(content)
    if (serialized === lastSaved.current) return
    setSaveState('unsaved')
    const timer = window.setTimeout(async () => {
      setSaveState('saving')
      const save = async () => {
        try {
          const saved = await saveCVGeneration(id, content, revisionRef.current)
          revisionRef.current = saved.revision
          lastSaved.current = serialized
          setGeneration(saved)
          setSaveState('saved')
          setRevisions(await getCVRevisions(id))
        } catch (error) {
          setSaveState('error')
          toast.error(error instanceof Error ? error.message : 'Autosave failed.')
        }
      }
      saveQueue.current = saveQueue.current.then(save, save)
      await saveQueue.current
    }, 900)
    return () => window.clearTimeout(timer)
  }, [content, id])

  const replace = (next: CVGeneration) => {
    setGeneration(next)
    setContent(next.content)
    revisionRef.current = next.revision
    lastSaved.current = JSON.stringify(next.content)
    setSaveState('saved')
    void getCVRevisions(id).then(setRevisions)
  }

  const updatePersonal = (key: keyof CVContent['personal_info'], value: string) => setContent((current) => current ? ({ ...current, personal_info: { ...current.personal_info, [key]: value } }) : current)
  const updateExperience = (index: number, patch: Partial<CVContent['experience'][number]>) => setContent((current) => current ? ({ ...current, experience: current.experience.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) }) : current)
  const updateEducation = (index: number, patch: Partial<CVContent['education'][number]>) => setContent((current) => current ? ({ ...current, education: current.education.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) }) : current)
  const updateProject = (index: number, patch: Partial<CVContent['projects'][number]>) => setContent((current) => current ? ({ ...current, projects: current.projects.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) }) : current)

  if (loading) return <ProtectedRoute><DashboardLayout><div className="py-20 text-center text-sm text-neutral-500">Loading your tailored CV…</div></DashboardLayout></ProtectedRoute>
  if (!generation || !content) return <ProtectedRoute><DashboardLayout><div className="py-20 text-center"><p className="text-neutral-700">This CV could not be opened.</p><Link href="/dashboard/recommendations" className="mt-3 inline-block text-sm text-brand-turquoise-700">Back to Job Match</Link></div></DashboardLayout></ProtectedRoute>

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <style jsx global>{`@media print { body * { visibility: hidden; } #cv-preview, #cv-preview * { visibility: visible; } #cv-preview { position: absolute; inset: 0; width: 100%; box-shadow: none; } }`}</style>
        <div className="mx-auto max-w-7xl print:max-w-none">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3 print:hidden">
            <div><Link href="/dashboard/recommendations" className="text-xs font-medium text-brand-turquoise-700">← Back to Job Match</Link><h1 className="mt-1 text-2xl font-bold text-neutral-900">CV for {generation.job_title}</h1><p className="text-sm text-neutral-500">{generation.company} · Your uploaded CV stays unchanged</p></div>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-flex items-center gap-1 text-xs ${saveState === 'error' ? 'text-rose-600' : 'text-neutral-500'}`}><Save className="h-3.5 w-3.5" />{saveState === 'saving' ? 'Saving…' : saveState === 'unsaved' ? 'Unsaved changes' : saveState === 'error' ? 'Save failed' : `Saved · v${generation.revision}`}</span>
              <button onClick={() => window.print()} className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs font-semibold"><Printer className="h-3.5 w-3.5" />Print / PDF</button>
              <button onClick={() => void downloadCVGeneration(id, `${generation.job_title}-CV.docx`).catch(() => toast.error('Download failed.'))} className="inline-flex items-center gap-1.5 rounded-lg bg-brand-turquoise-600 px-3 py-2 text-xs font-semibold text-white"><Download className="h-3.5 w-3.5" />DOCX</button>
            </div>
          </div>

          {generation.validation_warnings.length > 0 && <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 print:hidden"><strong>Review before applying.</strong> {generation.validation_warnings.join(' ')}</div>}

          <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(520px,0.95fr)]">
            <div className="space-y-4 print:hidden">
              <EditorSection title="Contact details"><div className="grid gap-3 sm:grid-cols-2">{(Object.keys(content.personal_info) as (keyof CVContent['personal_info'])[]).map((key) => <Field key={key} label={key.replace('_', ' ')} value={content.personal_info[key]} onChange={(value) => updatePersonal(key, value)} />)}</div></EditorSection>
              <EditorSection title="Professional summary"><textarea className={inputClass} rows={6} value={content.summary} onChange={(event) => setContent({ ...content, summary: event.target.value })} /></EditorSection>
              <EditorSection title="Skills"><div className="grid gap-3 sm:grid-cols-3">{(['technical', 'certifications', 'languages'] as const).map((key) => <LinesField key={key} label={`${key} (one per line)`} values={content.skills[key]} onChange={(values) => setContent({ ...content, skills: { ...content.skills, [key]: values } })} />)}</div></EditorSection>
              <EditorSection title="Experience" action={<AddButton label="Add experience" onClick={() => setContent({ ...content, experience: [...content.experience, { title: '', company: '', location: '', start_date: '', end_date: '', description: '', achievements: [] }] })} />}>{content.experience.map((item, index) => <div key={index} className="relative mb-5 grid gap-3 rounded-xl border border-neutral-100 p-3 pt-10 sm:grid-cols-2"><RemoveButton label="Remove experience" onClick={() => setContent({ ...content, experience: content.experience.filter((_, itemIndex) => itemIndex !== index) })} /><Field label="Role" value={item.title} onChange={(value) => updateExperience(index, { title: value })} /><Field label="Company" value={item.company} onChange={(value) => updateExperience(index, { company: value })} /><Field label="Location" value={item.location} onChange={(value) => updateExperience(index, { location: value })} /><div className="grid grid-cols-2 gap-2"><Field label="Start" value={item.start_date} onChange={(value) => updateExperience(index, { start_date: value })} /><Field label="End" value={item.end_date} onChange={(value) => updateExperience(index, { end_date: value })} /></div><label className="block sm:col-span-2"><span className="mb-1 block text-xs font-medium text-neutral-600">Description</span><textarea className={inputClass} rows={4} value={item.description} onChange={(event) => updateExperience(index, { description: event.target.value })} /></label><div className="sm:col-span-2"><LinesField label="Achievements (one per line)" values={item.achievements} onChange={(values) => updateExperience(index, { achievements: values })} /></div></div>)}</EditorSection>
              <EditorSection title="Education" action={<AddButton label="Add education" onClick={() => setContent({ ...content, education: [...content.education, { degree: '', institution: '', location: '', graduation_date: '', gpa: '' }] })} />}>{content.education.map((item, index) => <div key={index} className="relative mb-4 grid gap-3 rounded-xl border border-neutral-100 p-3 pt-10 sm:grid-cols-2"><RemoveButton label="Remove education" onClick={() => setContent({ ...content, education: content.education.filter((_, itemIndex) => itemIndex !== index) })} /><Field label="Qualification" value={item.degree} onChange={(value) => updateEducation(index, { degree: value })} /><Field label="Institution" value={item.institution} onChange={(value) => updateEducation(index, { institution: value })} /><Field label="Location" value={item.location} onChange={(value) => updateEducation(index, { location: value })} /><Field label="Graduation date" value={item.graduation_date} onChange={(value) => updateEducation(index, { graduation_date: value })} /><Field label="GPA / result" value={item.gpa} onChange={(value) => updateEducation(index, { gpa: value })} /></div>)}</EditorSection>
              <EditorSection title="Projects" action={<AddButton label="Add project" onClick={() => setContent({ ...content, projects: [...content.projects, { name: '', description: '', technologies: [], url: '' }] })} />}>{content.projects.map((item, index) => <div key={index} className="relative mb-4 grid gap-3 rounded-xl border border-neutral-100 p-3 pt-10"><RemoveButton label="Remove project" onClick={() => setContent({ ...content, projects: content.projects.filter((_, itemIndex) => itemIndex !== index) })} /><Field label="Project name" value={item.name} onChange={(value) => updateProject(index, { name: value })} /><Field label="Project URL" value={item.url} onChange={(value) => updateProject(index, { url: value })} /><label><span className="mb-1 block text-xs font-medium text-neutral-600">Description</span><textarea className={inputClass} rows={3} value={item.description} onChange={(event) => updateProject(index, { description: event.target.value })} /></label><LinesField label="Technologies (one per line)" values={item.technologies} onChange={(values) => updateProject(index, { technologies: values })} /></div>)}</EditorSection>
              <EditorSection title="Version history" icon={<History className="h-4 w-4" />}><div className="flex flex-wrap gap-2"><button onClick={() => void resetCVGeneration(id).then(replace).catch(() => toast.error('Could not reset the CV.'))} className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium"><RotateCcw className="h-3.5 w-3.5" />Reset to AI draft</button>{revisions.filter((item) => item.revision !== generation.revision).slice(0, 8).map((item) => <button key={item.revision} onClick={() => void restoreCVRevision(id, item.revision).then(replace).catch(() => toast.error('Could not restore that version.'))} className="inline-flex items-center gap-1 rounded-lg border border-neutral-200 px-2.5 py-2 text-xs"><Undo2 className="h-3 w-3" />v{item.revision}</button>)}</div></EditorSection>
            </div>
            <div className="sticky top-5 overflow-hidden rounded-xl border border-neutral-200 bg-neutral-100 p-3 print:static print:border-0 print:bg-white print:p-0"><CVPreview content={previewContent ?? content} /></div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

function EditorSection({ title, icon, action, children }: { title: string; icon?: React.ReactNode; action?: React.ReactNode; children: React.ReactNode }) {
  return <section className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm"><div className="mb-3 flex items-center gap-2"><h2 className="text-sm font-semibold text-neutral-900">{title}</h2>{icon}<div className="ml-auto">{action}</div></div>{children}</section>
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className="inline-flex items-center gap-1 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700"><Plus className="h-3.5 w-3.5" />{label}</button>
}

function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} aria-label={label} className="absolute right-2 top-2 rounded-md p-1.5 text-neutral-400 hover:bg-rose-50 hover:text-rose-600"><Trash2 className="h-3.5 w-3.5" /></button>
}
