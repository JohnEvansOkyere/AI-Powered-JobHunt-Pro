'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { CVSection } from '@/components/profile/CVSection'
import { useProfile } from '@/hooks/useProfile'
import { calculateProfileCompletion, getCompletionMessage } from '@/lib/profile-utils'
import type {
  UserProfile,
  UserProfileFormData,
  ExperienceItem,
  TechnicalSkill,
} from '@/types/profile'
import { useRouter } from 'next/navigation'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  User,
  Briefcase,
  Award,
  Settings,
  AlertCircle,
  Pencil,
  Check,
  X,
  Plus,
  Trash2,
  Sparkles,
} from 'lucide-react'

type SectionKey =
  | 'career'
  | 'skills'
  | 'experience'
  | 'style'
  | 'ai'

export default function ProfilePage() {
  const { profile, loading, saveProfile, saving } = useProfile()
  const router = useRouter()
  const [editing, setEditing] = useState<SectionKey | null>(null)

  if (loading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-turquoise-600" />
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (!profile) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-xl border border-neutral-200 p-8 text-center">
              <AlertCircle className="h-8 w-8 text-neutral-400 mx-auto mb-3" />
              <h2 className="text-base font-semibold text-neutral-900 mb-1">
                No profile found
              </h2>
              <p className="text-sm text-neutral-500 mb-5">
                Complete your profile to get personalized job matches.
              </p>
              <button
                onClick={() => router.push('/profile/setup')}
                className="inline-flex items-center px-4 py-2 bg-neutral-900 hover:bg-neutral-800 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Set up your profile
              </button>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  const completionPercentage = calculateProfileCompletion(profile)

  const handleSectionSave = async (data: UserProfileFormData) => {
    await saveProfile(data)
    setEditing(null)
  }

  const enterEdit = (key: SectionKey) => {
    setEditing(key)
  }

  const cancelEdit = () => {
    setEditing(null)
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-4xl mx-auto space-y-5">
          <header>
            <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">
              Your profile
            </h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              This is what we use to find roles for you. Edit any section below &mdash;
              changes save on their own.
            </p>
          </header>

          <CompletionCard percentage={completionPercentage} />

          <CVSection />

          <CareerTargetingSection
            profile={profile}
            isEditing={editing === 'career'}
            onEdit={() => enterEdit('career')}
            onCancel={cancelEdit}
            onSave={handleSectionSave}
            saving={saving}
          />

          <SkillsSection
            profile={profile}
            isEditing={editing === 'skills'}
            onEdit={() => enterEdit('skills')}
            onCancel={cancelEdit}
            onSave={handleSectionSave}
            saving={saving}
          />

          <ExperienceSection
            profile={profile}
            isEditing={editing === 'experience'}
            onEdit={() => enterEdit('experience')}
            onCancel={cancelEdit}
            onSave={handleSectionSave}
            saving={saving}
          />

          <ApplicationStyleSection
            profile={profile}
            isEditing={editing === 'style'}
            onEdit={() => enterEdit('style')}
            onCancel={cancelEdit}
            onSave={handleSectionSave}
            saving={saving}
          />

          <AIPreferencesSection
            profile={profile}
            isEditing={editing === 'ai'}
            onEdit={() => enterEdit('ai')}
            onCancel={cancelEdit}
            onSave={handleSectionSave}
            saving={saving}
          />

          <div className="pt-2 pb-8 text-center">
            <button
              onClick={() => router.push('/profile/setup')}
              className="text-xs text-neutral-500 hover:text-neutral-700 transition-colors underline-offset-2 hover:underline"
            >
              Prefer a guided walkthrough? Run the full setup &rarr;
            </button>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}

/* -------------------------------------------------------------------------- */
/*  Completion card                                                           */
/* -------------------------------------------------------------------------- */

function CompletionCard({ percentage }: { percentage: number }) {
  const message = getCompletionMessage(percentage)
  const isDone = percentage >= 100

  return (
    <section className="bg-white rounded-xl border border-neutral-200 p-5">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <h2 className="text-sm font-semibold text-neutral-900">
            Profile strength
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">{message}</p>
        </div>
        <div className="flex items-center gap-1.5">
          {isDone && (
            <Sparkles className="w-3.5 h-3.5 text-brand-turquoise-600" />
          )}
          <span className="text-lg font-semibold text-neutral-900 tabular-nums">
            {percentage}%
          </span>
        </div>
      </div>
      <div className="w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-turquoise-500 rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </section>
  )
}

/* -------------------------------------------------------------------------- */
/*  Editable section wrapper                                                  */
/* -------------------------------------------------------------------------- */

interface EditableSectionProps {
  icon: React.ReactNode
  title: string
  empty: boolean
  emptyLabel?: string
  isEditing: boolean
  onEdit: () => void
  onSave: () => void | Promise<void>
  onCancel: () => void
  canSave?: boolean
  saving?: boolean
  children: React.ReactNode
}

function EditableSection({
  icon,
  title,
  empty,
  emptyLabel = 'Empty',
  isEditing,
  onEdit,
  onSave,
  onCancel,
  canSave = true,
  saving,
  children,
}: EditableSectionProps) {
  return (
    <section className="bg-white rounded-xl border border-neutral-200 p-5">
      <header className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 text-neutral-600">{icon}</span>
          <h2 className="text-sm font-semibold text-neutral-900 truncate">
            {title}
          </h2>
          {empty && !isEditing && (
            <span className="ml-1 inline-flex items-center text-[10px] font-medium text-amber-700 bg-amber-50 border border-amber-100 rounded-md px-1.5 py-0.5 uppercase tracking-wide">
              {emptyLabel}
            </span>
          )}
        </div>
        {isEditing ? (
          <div className="flex items-center gap-1.5">
            <button
              onClick={onCancel}
              disabled={saving}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-white border border-neutral-200 hover:border-neutral-300 text-neutral-700 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
            >
              <X className="h-3.5 w-3.5" />
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={!canSave || saving}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-neutral-900 hover:bg-neutral-800 text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Check className="h-3.5 w-3.5" />
              {saving ? 'Saving\u2026' : 'Save'}
            </button>
          </div>
        ) : (
          <button
            onClick={onEdit}
            className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              empty
                ? 'bg-brand-turquoise-600 hover:bg-brand-turquoise-700 text-white'
                : 'bg-white border border-neutral-200 hover:border-neutral-300 text-neutral-700'
            }`}
          >
            {empty ? (
              <>
                <Plus className="h-3.5 w-3.5" />
                Add
              </>
            ) : (
              <>
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </>
            )}
          </button>
        )}
      </header>
      {children}
    </section>
  )
}

/* -------------------------------------------------------------------------- */
/*  Career targeting                                                          */
/* -------------------------------------------------------------------------- */

interface SectionProps {
  profile: UserProfile
  isEditing: boolean
  onEdit: () => void
  onCancel: () => void
  onSave: (data: UserProfileFormData) => Promise<void>
  saving: boolean
}

function CareerTargetingSection({
  profile,
  isEditing,
  onEdit,
  onCancel,
  onSave,
  saving,
}: SectionProps) {
  const initialTitles = useMemo(() => {
    const titles: string[] = []
    if (profile.primary_job_title) titles.push(profile.primary_job_title)
    if (profile.secondary_job_titles) titles.push(...profile.secondary_job_titles)
    return titles
  }, [profile.primary_job_title, profile.secondary_job_titles])

  const [titles, setTitles] = useState<string[]>(initialTitles)
  const [seniority, setSeniority] = useState<string>(profile.seniority_level || '')
  const [workPref, setWorkPref] = useState<string>(profile.work_preference || '')
  const [industries, setIndustries] = useState<string[]>(profile.desired_industries || [])

  useEffect(() => {
    if (!isEditing) {
      setTitles(initialTitles)
      setSeniority(profile.seniority_level || '')
      setWorkPref(profile.work_preference || '')
      setIndustries(profile.desired_industries || [])
    }
  }, [isEditing, initialTitles, profile.seniority_level, profile.work_preference, profile.desired_industries])

  const isEmpty =
    !profile.primary_job_title && !profile.seniority_level && !profile.work_preference

  const handleSave = async () => {
    await onSave({
      primary_job_title: titles[0] || '',
      secondary_job_titles: titles.slice(1),
      seniority_level: (seniority || null) as UserProfile['seniority_level'],
      work_preference: (workPref || null) as UserProfile['work_preference'],
      desired_industries: industries,
    })
  }

  return (
    <EditableSection
      icon={<User className="h-4 w-4" />}
      title="Career targeting"
      empty={isEmpty}
      isEditing={isEditing}
      onEdit={onEdit}
      onCancel={onCancel}
      onSave={handleSave}
      saving={saving}
    >
      {isEditing ? (
        <div className="space-y-4">
          <div>
            <FieldLabel>Target job titles</FieldLabel>
            <ChipInput
              values={titles}
              onChange={setTitles}
              placeholder="e.g. Senior ML Engineer, Data Scientist"
              firstChipLabel="primary"
            />
            <FieldHelper>
              Your first title is treated as your primary role. Add up to 5 &mdash;
              the more specific, the better.
            </FieldHelper>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-neutral-100">
            <div>
              <FieldLabel>Seniority</FieldLabel>
              <Select value={seniority} onChange={setSeniority}>
                <option value="">Not set</option>
                <option value="entry">Entry level</option>
                <option value="mid">Mid level</option>
                <option value="senior">Senior</option>
                <option value="lead">Lead</option>
                <option value="executive">Executive</option>
              </Select>
            </div>
            <div>
              <FieldLabel>Where you want to work</FieldLabel>
              <Select value={workPref} onChange={setWorkPref}>
                <option value="">Not set</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">On-site</option>
                <option value="flexible">Flexible</option>
              </Select>
            </div>
          </div>

          <div>
            <FieldLabel>Industries you&rsquo;re drawn to</FieldLabel>
            <ChipInput
              values={industries}
              onChange={setIndustries}
              placeholder="e.g. Fintech, Healthtech, Climate"
            />
            <FieldHelper>Optional &mdash; helps us weight industry fit.</FieldHelper>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <ReadLabel>Target job titles</ReadLabel>
            {profile.primary_job_title ||
            (profile.secondary_job_titles && profile.secondary_job_titles.length > 0) ? (
              <div className="flex flex-wrap gap-1.5">
                {profile.primary_job_title && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-brand-turquoise-700 bg-brand-turquoise-50 border border-brand-turquoise-100 rounded-md">
                    {profile.primary_job_title}
                    <span className="text-[10px] text-brand-turquoise-600">primary</span>
                  </span>
                )}
                {profile.secondary_job_titles?.map((title, index) => (
                  <span
                    key={index}
                    className="px-2 py-0.5 text-xs font-medium text-neutral-700 bg-neutral-50 border border-neutral-200 rounded-md"
                  >
                    {title}
                  </span>
                ))}
              </div>
            ) : (
              <EmptyHint>No target titles yet</EmptyHint>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-neutral-100">
            <InfoField
              label="Seniority"
              value={formatSeniority(profile.seniority_level)}
            />
            <InfoField
              label="Where you want to work"
              value={formatWorkPreference(profile.work_preference)}
            />
            {profile.desired_industries && profile.desired_industries.length > 0 && (
              <div className="md:col-span-2">
                <ReadLabel>Industries</ReadLabel>
                <p className="text-sm text-neutral-900">
                  {profile.desired_industries.join(', ')}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </EditableSection>
  )
}

/* -------------------------------------------------------------------------- */
/*  Skills                                                                    */
/* -------------------------------------------------------------------------- */

function SkillsSection({
  profile,
  isEditing,
  onEdit,
  onCancel,
  onSave,
  saving,
}: SectionProps) {
  const initialTech = useMemo<string[]>(
    () => (profile.technical_skills || []).map((s) => s.skill),
    [profile.technical_skills],
  )
  const [technical, setTechnical] = useState<string[]>(initialTech)
  const [soft, setSoft] = useState<string[]>(profile.soft_skills || [])

  useEffect(() => {
    if (!isEditing) {
      setTechnical(initialTech)
      setSoft(profile.soft_skills || [])
    }
  }, [isEditing, initialTech, profile.soft_skills])

  const isEmpty =
    (!profile.technical_skills || profile.technical_skills.length === 0) &&
    (!profile.soft_skills || profile.soft_skills.length === 0)

  const handleSave = async () => {
    const existingByName = new Map(
      (profile.technical_skills || []).map((s) => [s.skill, s]),
    )
    const technical_skills: TechnicalSkill[] = technical.map((name) => {
      const existing = existingByName.get(name)
      return existing
        ? { skill: name, years: existing.years, confidence: existing.confidence }
        : { skill: name }
    })
    await onSave({
      technical_skills,
      soft_skills: soft,
    })
  }

  return (
    <EditableSection
      icon={<Award className="h-4 w-4" />}
      title="Skills & expertise"
      empty={isEmpty}
      isEditing={isEditing}
      onEdit={onEdit}
      onCancel={onCancel}
      onSave={handleSave}
      saving={saving}
    >
      {isEditing ? (
        <div className="space-y-4">
          <div>
            <FieldLabel>Technical skills</FieldLabel>
            <ChipInput
              values={technical}
              onChange={setTechnical}
              placeholder="e.g. Python, PyTorch, SQL, AWS"
            />
            <FieldHelper>
              Press Enter or comma to add. These matter most for matching.
            </FieldHelper>
          </div>
          <div>
            <FieldLabel>Soft skills</FieldLabel>
            <ChipInput
              values={soft}
              onChange={setSoft}
              placeholder="e.g. Communication, Mentorship, Problem-solving"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {profile.technical_skills && profile.technical_skills.length > 0 ? (
            <div>
              <ReadLabel>Technical</ReadLabel>
              <div className="flex flex-wrap gap-1.5">
                {profile.technical_skills.map((skill, index) => (
                  <span
                    key={index}
                    className="px-2 py-0.5 text-xs font-medium text-neutral-700 bg-neutral-50 border border-neutral-200 rounded-md"
                  >
                    {skill.skill}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <ReadLabel>Technical</ReadLabel>
              <EmptyHint>None added yet</EmptyHint>
            </div>
          )}

          {profile.soft_skills && profile.soft_skills.length > 0 ? (
            <div>
              <ReadLabel>Soft</ReadLabel>
              <div className="flex flex-wrap gap-1.5">
                {profile.soft_skills.map((skill, index) => (
                  <span
                    key={index}
                    className="px-2 py-0.5 text-xs font-medium text-neutral-700 bg-neutral-50 border border-neutral-200 rounded-md"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <ReadLabel>Soft</ReadLabel>
              <EmptyHint>None added yet</EmptyHint>
            </div>
          )}
        </div>
      )}
    </EditableSection>
  )
}

/* -------------------------------------------------------------------------- */
/*  Work experience                                                           */
/* -------------------------------------------------------------------------- */

function ExperienceSection({
  profile,
  isEditing,
  onEdit,
  onCancel,
  onSave,
  saving,
}: SectionProps) {
  const [items, setItems] = useState<ExperienceItem[]>(profile.experience || [])
  const [achievementsDrafts, setAchievementsDrafts] = useState<string[]>([])

  useEffect(() => {
    if (!isEditing) {
      setItems(profile.experience || [])
      setAchievementsDrafts(
        (profile.experience || []).map((e) => (e.achievements || []).join(', ')),
      )
    }
  }, [isEditing, profile.experience])

  const isEmpty = !profile.experience || profile.experience.length === 0

  const update = (index: number, patch: Partial<ExperienceItem>) => {
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))
  }

  const updateAchievements = (index: number, raw: string) => {
    setAchievementsDrafts((prev) => {
      const next = [...prev]
      next[index] = raw
      return next
    })
    const list = raw.split(',').map((s) => s.trim()).filter(Boolean)
    update(index, { achievements: list })
  }

  const addItem = () => {
    setItems((prev) => [
      ...prev,
      { role: '', company: '', duration: '', achievements: [] },
    ])
    setAchievementsDrafts((prev) => [...prev, ''])
  }

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index))
    setAchievementsDrafts((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSave = async () => {
    const cleaned = items
      .map((item) => ({
        role: item.role.trim(),
        company: item.company.trim(),
        duration: item.duration.trim(),
        achievements: (item.achievements || []).map((a) => a.trim()).filter(Boolean),
      }))
      .filter((item) => item.role || item.company)
    await onSave({ experience: cleaned })
  }

  const canSave = items.every((i) => !!(i.role && i.company) || (!i.role && !i.company))

  return (
    <EditableSection
      icon={<Briefcase className="h-4 w-4" />}
      title="Work experience"
      empty={isEmpty}
      isEditing={isEditing}
      onEdit={onEdit}
      onCancel={onCancel}
      onSave={handleSave}
      canSave={canSave}
      saving={saving}
    >
      {isEditing ? (
        <div className="space-y-4">
          {items.length === 0 && (
            <p className="text-sm text-neutral-500">
              Add your most recent roles first &mdash; we use these to read seniority and
              domain fit.
            </p>
          )}
          {items.map((item, index) => (
            <div
              key={index}
              className="rounded-lg border border-neutral-200 bg-neutral-50/60 p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                  Role {index + 1}
                </span>
                <button
                  onClick={() => removeItem(index)}
                  className="inline-flex items-center gap-1 text-xs text-neutral-500 hover:text-red-600 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <FieldLabel>Role</FieldLabel>
                  <TextInput
                    value={item.role}
                    onChange={(v) => update(index, { role: v })}
                    placeholder="e.g. Senior ML Engineer"
                  />
                </div>
                <div>
                  <FieldLabel>Company</FieldLabel>
                  <TextInput
                    value={item.company}
                    onChange={(v) => update(index, { company: v })}
                    placeholder="e.g. Spotify"
                  />
                </div>
                <div className="md:col-span-2">
                  <FieldLabel>When</FieldLabel>
                  <TextInput
                    value={item.duration}
                    onChange={(v) => update(index, { duration: v })}
                    placeholder="e.g. Jan 2022 – Present"
                  />
                </div>
                <div className="md:col-span-2">
                  <FieldLabel>What you did (comma-separated)</FieldLabel>
                  <textarea
                    value={achievementsDrafts[index] || ''}
                    onChange={(e) => updateAchievements(index, e.target.value)}
                    placeholder="Led training pipeline, shipped recommender, mentored 2 engineers"
                    rows={3}
                    className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-lg focus:ring-1 focus:ring-brand-turquoise-500 focus:border-brand-turquoise-500 bg-white"
                  />
                </div>
              </div>
            </div>
          ))}

          <button
            onClick={addItem}
            className="w-full py-2.5 border-2 border-dashed border-neutral-300 rounded-lg text-sm text-neutral-600 hover:border-brand-turquoise-400 hover:text-brand-turquoise-700 hover:bg-brand-turquoise-50/40 transition-colors font-medium"
          >
            <Plus className="inline h-3.5 w-3.5 mr-1" />
            Add another role
          </button>
        </div>
      ) : profile.experience && profile.experience.length > 0 ? (
        <div className="space-y-3">
          {profile.experience.map((exp, index) => (
            <div key={index} className="rounded-lg border border-neutral-200 p-3">
              <h3 className="text-sm font-semibold text-neutral-900">{exp.role}</h3>
              <p className="text-xs text-neutral-600 mt-0.5">
                {exp.company}
                {exp.duration && (
                  <span className="text-neutral-400"> · {exp.duration}</span>
                )}
              </p>
              {exp.achievements && exp.achievements.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {exp.achievements.map((achievement, idx) => (
                    <li
                      key={idx}
                      className="text-xs text-neutral-700 flex items-start gap-1.5"
                    >
                      <span className="text-neutral-400 mt-[3px]">•</span>
                      <span>{achievement}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyHint>
          No roles yet &mdash; adding two or three helps us spot the right match much
          faster.
        </EmptyHint>
      )}
    </EditableSection>
  )
}

/* -------------------------------------------------------------------------- */
/*  Application style                                                         */
/* -------------------------------------------------------------------------- */

function ApplicationStyleSection({
  profile,
  isEditing,
  onEdit,
  onCancel,
  onSave,
  saving,
}: SectionProps) {
  const [tone, setTone] = useState<string>(profile.writing_tone || '')

  useEffect(() => {
    if (!isEditing) {
      setTone(profile.writing_tone || '')
    }
  }, [isEditing, profile.writing_tone])

  const isEmpty = !profile.writing_tone

  const handleSave = async () => {
    await onSave({
      writing_tone: (tone || null) as UserProfile['writing_tone'],
    })
  }

  return (
    <EditableSection
      icon={<Settings className="h-4 w-4" />}
      title="Application style"
      empty={isEmpty}
      isEditing={isEditing}
      onEdit={onEdit}
      onCancel={onCancel}
      onSave={handleSave}
      saving={saving}
    >
      {isEditing ? (
        <div>
          <FieldLabel>Writing tone</FieldLabel>
          <Select value={tone} onChange={setTone}>
            <option value="">Not set</option>
            <option value="professional">Professional</option>
            <option value="formal">Formal</option>
            <option value="friendly">Friendly</option>
            <option value="confident">Confident</option>
          </Select>
          <FieldHelper>Used when AI drafts anything on your behalf.</FieldHelper>
        </div>
      ) : (
        <InfoField label="Writing tone" value={profile.writing_tone} capitalize />
      )}
    </EditableSection>
  )
}

/* -------------------------------------------------------------------------- */
/*  AI preferences                                                            */
/* -------------------------------------------------------------------------- */

function AIPreferencesSection({
  profile,
  isEditing,
  onEdit,
  onCancel,
  onSave,
  saving,
}: SectionProps) {
  const [speed, setSpeed] = useState<string>(
    profile.ai_preferences?.speed_vs_quality || '',
  )

  useEffect(() => {
    if (!isEditing) {
      setSpeed(profile.ai_preferences?.speed_vs_quality || '')
    }
  }, [isEditing, profile.ai_preferences?.speed_vs_quality])

  const isEmpty = !profile.ai_preferences?.speed_vs_quality

  const handleSave = async () => {
    await onSave({
      ai_preferences: {
        ...profile.ai_preferences,
        speed_vs_quality:
          (speed || undefined) as 'speed' | 'quality' | 'balanced' | undefined,
      },
    })
  }

  return (
    <EditableSection
      icon={<Sparkles className="h-4 w-4" />}
      title="AI preferences"
      empty={isEmpty}
      isEditing={isEditing}
      onEdit={onEdit}
      onCancel={onCancel}
      onSave={handleSave}
      saving={saving}
    >
      {isEditing ? (
        <div>
          <FieldLabel>Speed vs quality</FieldLabel>
          <Select value={speed} onChange={setSpeed}>
            <option value="">Not set</option>
            <option value="speed">Faster (quick results)</option>
            <option value="balanced">Balanced (recommended)</option>
            <option value="quality">Higher quality (takes longer)</option>
          </Select>
          <FieldHelper>Affects how we pick AI models for your drafts.</FieldHelper>
        </div>
      ) : (
        <InfoField
          label="Speed vs quality"
          value={formatSpeed(profile.ai_preferences?.speed_vs_quality)}
        />
      )}
    </EditableSection>
  )
}

/* -------------------------------------------------------------------------- */
/*  Shared primitives                                                         */
/* -------------------------------------------------------------------------- */

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="text-xs font-medium text-neutral-600 mb-1.5 block">
      {children}
    </label>
  )
}

function FieldHelper({ children }: { children: React.ReactNode }) {
  return <p className="text-xs text-neutral-500 mt-1.5">{children}</p>
}

function ReadLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="text-[10px] font-medium text-neutral-500 mb-1.5 block uppercase tracking-wide">
      {children}
    </label>
  )
}

function EmptyHint({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-neutral-400">{children}</p>
}

function TextInput({
  value,
  onChange,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-lg focus:ring-1 focus:ring-brand-turquoise-500 focus:border-brand-turquoise-500 bg-white"
    />
  )
}

function Select({
  value,
  onChange,
  children,
}: {
  value: string
  onChange: (v: string) => void
  children: React.ReactNode
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 text-sm border border-neutral-300 rounded-lg focus:ring-1 focus:ring-brand-turquoise-500 focus:border-brand-turquoise-500 bg-white"
    >
      {children}
    </select>
  )
}

interface ChipInputProps {
  values: string[]
  onChange: (next: string[]) => void
  placeholder?: string
  firstChipLabel?: string
}

function ChipInput({ values, onChange, placeholder, firstChipLabel }: ChipInputProps) {
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const commit = () => {
    const raw = draft.trim()
    if (!raw) return
    const parts = raw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
      .filter((s) => !values.includes(s))
    if (parts.length === 0) {
      setDraft('')
      return
    }
    onChange([...values, ...parts])
    setDraft('')
  }

  const remove = (v: string) => {
    onChange(values.filter((x) => x !== v))
  }

  return (
    <div
      className="w-full min-h-[42px] px-2 py-1.5 border border-neutral-300 rounded-lg bg-white focus-within:ring-1 focus-within:ring-brand-turquoise-500 focus-within:border-brand-turquoise-500"
      onClick={() => inputRef.current?.focus()}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        {values.map((v, i) => (
          <span
            key={`${v}-${i}`}
            className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-md ${
              firstChipLabel && i === 0
                ? 'text-brand-turquoise-700 bg-brand-turquoise-50 border border-brand-turquoise-100'
                : 'text-neutral-700 bg-neutral-50 border border-neutral-200'
            }`}
          >
            {v}
            {firstChipLabel && i === 0 && (
              <span className="text-[10px] text-brand-turquoise-600">{firstChipLabel}</span>
            )}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                remove(v)
              }}
              className="text-neutral-500 hover:text-neutral-900"
              aria-label={`Remove ${v}`}
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault()
              commit()
            } else if (e.key === 'Backspace' && !draft && values.length > 0) {
              onChange(values.slice(0, -1))
            }
          }}
          onBlur={commit}
          placeholder={values.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[120px] px-1 py-0.5 text-sm bg-transparent outline-none"
        />
      </div>
    </div>
  )
}

function InfoField({
  label,
  value,
  capitalize = false,
}: {
  label: string
  value: string | null | undefined
  capitalize?: boolean
}) {
  return (
    <div>
      <ReadLabel>{label}</ReadLabel>
      <p
        className={`text-sm ${
          value ? 'text-neutral-900' : 'text-neutral-400'
        } ${capitalize ? 'capitalize' : ''}`}
      >
        {value || 'Not set'}
      </p>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Formatters                                                                */
/* -------------------------------------------------------------------------- */

function formatSeniority(level?: string | null): string | undefined {
  if (!level) return undefined
  const map: Record<string, string> = {
    entry: 'Entry level',
    mid: 'Mid level',
    senior: 'Senior',
    lead: 'Lead',
    executive: 'Executive',
  }
  return map[level] || level
}

function formatWorkPreference(pref?: string | null): string | undefined {
  if (!pref) return undefined
  const map: Record<string, string> = {
    remote: 'Remote',
    hybrid: 'Hybrid',
    onsite: 'On-site',
    flexible: 'Flexible',
  }
  return map[pref] || pref
}

function formatSpeed(pref?: string | null): string | undefined {
  if (!pref) return undefined
  const map: Record<string, string> = {
    speed: 'Faster (quick results)',
    balanced: 'Balanced',
    quality: 'Higher quality',
  }
  return map[pref] || pref
}
