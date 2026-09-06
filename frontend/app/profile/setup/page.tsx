'use client'

import { useEffect, useRef, useState, type FormEvent } from 'react'
import Link from 'next/link'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { useAuth } from '@/hooks/useAuth'
import { getMyProfile, updateProfile } from '@/lib/api/profiles'
import { triggerRegenerate } from '@/lib/api/recommendations'
import type { UserProfileFormData } from '@/types/profile'
import { CVSection } from '@/components/profile/CVSection'
import { getActiveCV, isCVReady } from '@/lib/api/cvs'
import { isMatchingProfileReady } from '@/lib/profile-utils'

export default function ProfileSetupPage() {
  return <ProtectedRoute><ProfileSetup /></ProtectedRoute>
}

function ProfileSetup() {
  const { user, logout } = useAuth()
  const [data, setData] = useState<UserProfileFormData>({})
  const [skills, setSkills] = useState('')
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [complete, setComplete] = useState(false)
  const [matchMessage, setMatchMessage] = useState('')
  const [cvReady, setCVReady] = useState(false)
  const heading = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    let active = true
    if (!user?.id) return
    getMyProfile().then((profile) => {
      if (!active) return
      setData(profile)
      setSkills((profile.technical_skills || []).map(({ skill }) => skill).join(', '))
      setStep(isMatchingProfileReady(profile) ? 3 : profile.primary_job_title?.trim() && profile.seniority_level && profile.work_preference ? 2 : 1)
      setLoading(false)
    }).catch(() => {
      if (!active) return
      setError('We couldn’t load your saved details. Please try again.')
      setLoading(false)
    })
    return () => { active = false }
  }, [user?.id, attempt])

  useEffect(() => { if (!loading) heading.current?.focus() }, [step, loading, complete])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (saving) return
    setError('')
    const names = Array.from(new Set(skills.split(/[,\n]/).map((skill) => skill.trim()).filter(Boolean)))
    if (step === 1 && !data.primary_job_title?.trim()) {
      setError('Enter a target job title to continue.')
      return
    }
    if (step === 2 && (names.length === 0 || names.length > 30 || names.some((skill) => skill.length > 100))) {
      setError('Add between 1 and 30 skills, with each skill at most 100 characters.')
      return
    }
    setSaving(true)
    try {
      if (step < 3) {
        const changes: UserProfileFormData = step === 1 ? {
          primary_job_title: data.primary_job_title?.trim(),
          seniority_level: data.seniority_level,
          work_preference: data.work_preference,
          local_job_market: data.local_job_market?.trim() || undefined,
        } : {
          technical_skills: names.map((skill) => data.technical_skills?.find((existing) => existing.skill.toLowerCase() === skill.toLowerCase()) || { skill }),
        }
        const saved = await updateProfile(changes)
        setData(saved)
        setStep(step + 1)
      } else {
        if (!isCVReady(await getActiveCV())) {
          setCVReady(false)
          setError('Upload a CV and wait for it to finish processing before continuing.')
          return
        }
        // A failed matching request must not undo a successfully saved profile.
        try {
          const result = await triggerRegenerate()
          setMatchMessage(result.status === 'already_fresh'
            ? 'Your recent job matches are ready to view.'
            : 'We’ve requested your job matches. They may take a few minutes to appear.')
        } catch {
          setMatchMessage('Your details are saved, but we couldn’t start matching now. Open Job matches and use Refresh matches to try again later.')
        }
        setComplete(true)
      }
    } catch {
      setError(step === 3 ? 'We couldn’t verify your CV. Please try again; your saved details are still here.' : 'Your changes weren’t saved. Please try again; your entries are still here.')
    } finally {
      setSaving(false)
    }
  }

  const fieldClass = 'mt-2 block w-full rounded-lg border border-neutral-300 bg-white px-3 py-3 text-base text-neutral-900 focus:outline-none focus:ring-2 focus:ring-emerald-700'

  return (
    <main className="min-h-screen bg-neutral-50 px-4 py-8 text-neutral-900 sm:py-12">
      <div className="mx-auto max-w-xl">
        <nav aria-label="Setup navigation" className="mb-10 flex items-center justify-between text-sm">
          <Link href="/jobs" className="underline underline-offset-4">Browse jobs</Link>
          <button onClick={logout} className="underline underline-offset-4">Sign out</button>
        </nav>
        <section className="rounded-2xl border border-neutral-200 bg-white p-6 sm:p-8">
          {loading ? <p role="status">Loading your details…</p> : !data.id ? <>
            <h1 className="text-xl font-semibold">Let’s get your profile ready</h1>
            <p role="alert" className="my-4">{error}</p>
            <button className="btn-primary" onClick={() => { setLoading(true); setError(''); setAttempt((value) => value + 1) }}>Try again</button>
          </> : complete ? <>
            <p className="mb-3 text-sm font-medium text-emerald-800">Setup complete</p>
            <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold">Your profile is ready for matching</h1>
            <p role="status" className="mt-4 text-neutral-600">{matchMessage}</p>
            <Link href="/dashboard/recommendations" className="mt-6 block rounded-lg bg-emerald-800 px-5 py-3 text-center font-semibold text-white">View job matches</Link>
            <Link href="/dashboard/profile" className="mt-4 block text-center text-sm underline">Review your CV and profile</Link>
          </> : <>
            <p className="mb-3 text-sm font-medium text-emerald-800">Step {step} of 3 · {step === 1 ? 'Your next role' : step === 2 ? 'Your skills' : 'Your CV'}</p>
            <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold">{step === 1 ? 'What kind of work are you looking for?' : step === 2 ? 'What skills will you bring?' : 'Upload your CV to complete setup'}</h1>
            <p className="mt-3 text-sm leading-6 text-neutral-600">{step === 1 ? 'Tell us what you’re aiming for so we can recommend relevant jobs.' : step === 2 ? 'Include skills from work, study or personal projects.' : 'We need your CV alongside your profile to match your experience to jobs and create tailored CVs. Wait until your file is ready before continuing.'}</p>
            {step === 3 && <div className="mt-6"><CVSection onReadyChange={setCVReady} disabled={saving} /></div>}
            <form onSubmit={submit} method="post" className="mt-6 space-y-5">
              {step < 3 && <fieldset disabled={saving} className="space-y-5">
                <legend className="sr-only">{step === 1 ? 'Career preferences' : 'Skills'}</legend>
                {step === 1 ? <>
                  <label className="block text-sm font-medium">Target job title
                    <input className={fieldClass} required maxLength={150} value={data.primary_job_title || ''} onChange={(e) => setData({ ...data, primary_job_title: e.target.value })} placeholder="e.g. Accountant" />
                  </label>
                  <label className="block text-sm font-medium">Experience level
                    <select className={fieldClass} required value={data.seniority_level || ''} onChange={(e) => setData({ ...data, seniority_level: e.target.value as UserProfileFormData['seniority_level'] })}>
                      <option value="">Choose your level</option><option value="entry">Entry level / first job</option><option value="mid">Mid level</option><option value="senior">Senior</option><option value="lead">Team lead</option><option value="executive">Executive</option>
                    </select>
                  </label>
                  <label className="block text-sm font-medium">Work preference
                    <select className={fieldClass} required value={data.work_preference || ''} onChange={(e) => setData({ ...data, work_preference: e.target.value as UserProfileFormData['work_preference'] })}>
                      <option value="">Choose a preference</option><option value="onsite">On site</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="flexible">Open to any</option>
                    </select>
                  </label>
                  <label className="block text-sm font-medium">Preferred job market (optional)
                    <input className={fieldClass} maxLength={100} value={data.local_job_market || ''} onChange={(e) => setData({ ...data, local_job_market: e.target.value })} placeholder="e.g. Ghana" />
                  </label>
                </> : <div>
                  <label htmlFor="setup-skills" className="block text-sm font-medium">Your skills</label>
                  <textarea id="setup-skills" className={fieldClass} required rows={4} maxLength={3000} value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="e.g. Excel, bookkeeping, customer service" aria-describedby="skills-help" />
                  <p id="skills-help" className="mt-2 text-sm text-neutral-600">Separate each skill with a comma. Add at least one.</p>
                </div>}
              </fieldset>}
              {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
              <div className="flex items-center justify-between gap-4 border-t border-neutral-200 pt-5">
                {step > 1 && <button type="button" disabled={saving} className="text-sm underline disabled:opacity-50" onClick={() => { setError(''); setStep(step - 1) }}>Back</button>}
                <button type="submit" disabled={saving || (step === 3 && !cvReady)} className="ml-auto rounded-lg bg-emerald-800 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-900 disabled:opacity-50">{saving ? 'Saving…' : step < 3 ? 'Save and continue' : 'Find my job matches'}</button>
              </div>
              <p className="text-xs leading-5 text-neutral-500">Your progress is saved after each step. You can edit these details in Profile later.</p>
            </form>
          </>}
        </section>
      </div>
    </main>
  )
}
