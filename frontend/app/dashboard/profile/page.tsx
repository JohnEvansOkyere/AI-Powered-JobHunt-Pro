'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { CVSection } from '@/components/profile/CVSection'
import { useProfile } from '@/hooks/useProfile'
import { calculateProfileCompletion, getMissingSections } from '@/lib/profile-utils'
import { useRouter } from 'next/navigation'
import {
  User,
  Briefcase,
  Award,
  Settings,
  AlertCircle,
  Pencil,
} from 'lucide-react'

export default function ProfilePage() {
  const { profile, loading } = useProfile()
  const router = useRouter()

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
                Complete profile
              </button>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  const completionPercentage = calculateProfileCompletion(profile)
  const missingSections = getMissingSections(profile)

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="max-w-4xl mx-auto space-y-5">
          {/* Header */}
          <header className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-neutral-900 tracking-tight">
                Your profile
              </h1>
              <p className="text-sm text-neutral-500 mt-0.5">
                This is what we use to rank roles for you.
              </p>
            </div>
            <button
              onClick={() => router.push('/profile/setup')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-neutral-200 hover:border-neutral-300 text-neutral-700 rounded-lg text-sm font-medium transition-colors"
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit
            </button>
          </header>

          {/* Completion */}
          <section className="bg-white rounded-xl border border-neutral-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-neutral-900">
                Profile completion
              </h2>
              <span className="text-sm font-semibold text-neutral-900 tabular-nums">
                {completionPercentage}%
              </span>
            </div>
            <div className="w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-turquoise-500 rounded-full transition-all duration-500"
                style={{ width: `${completionPercentage}%` }}
              />
            </div>
            {missingSections.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-neutral-500 mr-1">Still missing:</span>
                {missingSections.map((section) => (
                  <span
                    key={section}
                    className="inline-flex items-center text-xs text-neutral-700 bg-neutral-50 border border-neutral-200 rounded-md px-1.5 py-0.5"
                  >
                    {section}
                  </span>
                ))}
              </div>
            )}
          </section>

          {/* CV upload + management */}
          <CVSection />

          {/* Career Targeting */}
          <section className="bg-white rounded-xl border border-neutral-200 p-5">
            <header className="flex items-center gap-2 mb-4">
              <User className="h-4 w-4 text-neutral-600" />
              <h2 className="text-sm font-semibold text-neutral-900">
                Career targeting
              </h2>
            </header>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-neutral-500 mb-1.5 block uppercase tracking-wide">
                  Target job titles
                </label>
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
                  <p className="text-sm text-neutral-400">Not specified</p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-neutral-100">
                <InfoField
                  label="Seniority"
                  value={profile.seniority_level}
                  capitalize
                />
                <InfoField
                  label="Work preference"
                  value={profile.work_preference}
                  capitalize
                />
                {profile.desired_industries && profile.desired_industries.length > 0 && (
                  <div className="md:col-span-2">
                    <label className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
                      Industries
                    </label>
                    <p className="text-sm text-neutral-900 mt-1">
                      {profile.desired_industries.join(', ')}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Skills */}
          <section className="bg-white rounded-xl border border-neutral-200 p-5">
            <header className="flex items-center gap-2 mb-4">
              <Award className="h-4 w-4 text-neutral-600" />
              <h2 className="text-sm font-semibold text-neutral-900">
                Skills & expertise
              </h2>
            </header>

            {profile.technical_skills && profile.technical_skills.length > 0 && (
              <div className="mb-4">
                <label className="text-xs font-medium text-neutral-500 mb-1.5 block uppercase tracking-wide">
                  Technical
                </label>
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
            )}

            {profile.soft_skills && profile.soft_skills.length > 0 && (
              <div>
                <label className="text-xs font-medium text-neutral-500 mb-1.5 block uppercase tracking-wide">
                  Soft
                </label>
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
            )}

            {(!profile.technical_skills || profile.technical_skills.length === 0) &&
              (!profile.soft_skills || profile.soft_skills.length === 0) && (
                <p className="text-sm text-neutral-400">No skills added yet</p>
              )}
          </section>

          {/* Experience */}
          <section className="bg-white rounded-xl border border-neutral-200 p-5">
            <header className="flex items-center gap-2 mb-4">
              <Briefcase className="h-4 w-4 text-neutral-600" />
              <h2 className="text-sm font-semibold text-neutral-900">
                Work experience
              </h2>
            </header>
            {profile.experience && profile.experience.length > 0 ? (
              <div className="space-y-3">
                {profile.experience.map((exp, index) => (
                  <div
                    key={index}
                    className="rounded-lg border border-neutral-200 p-3"
                  >
                    <h3 className="text-sm font-semibold text-neutral-900">
                      {exp.role}
                    </h3>
                    <p className="text-xs text-neutral-600 mt-0.5">
                      {exp.company}
                      {exp.duration && <span className="text-neutral-400"> · {exp.duration}</span>}
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
              <p className="text-sm text-neutral-400">No experience added yet</p>
            )}
          </section>

          {/* Preferences */}
          <section className="bg-white rounded-xl border border-neutral-200 p-5">
            <header className="flex items-center gap-2 mb-4">
              <Settings className="h-4 w-4 text-neutral-600" />
              <h2 className="text-sm font-semibold text-neutral-900">Preferences</h2>
            </header>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoField
                label="Writing tone"
                value={profile.writing_tone}
                capitalize
              />
              {profile.ai_preferences?.speed_vs_quality && (
                <InfoField
                  label="AI speed vs quality"
                  value={profile.ai_preferences.speed_vs_quality}
                  capitalize
                />
              )}
            </div>
          </section>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
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
      <label className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
        {label}
      </label>
      <p
        className={`text-sm mt-1 ${
          value ? 'text-neutral-900' : 'text-neutral-400'
        } ${capitalize ? 'capitalize' : ''}`}
      >
        {value || 'Not specified'}
      </p>
    </div>
  )
}
