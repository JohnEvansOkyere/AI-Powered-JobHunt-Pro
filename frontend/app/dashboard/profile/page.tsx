'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { useProfile } from '@/hooks/useProfile'
import { calculateProfileCompletion, getMissingSections } from '@/lib/profile-utils'
import { useRouter } from 'next/navigation'
import { User, Briefcase, Award, Settings, AlertCircle } from 'lucide-react'

export default function ProfilePage() {
  const { profile, loading } = useProfile()
  const router = useRouter()

  if (loading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-700"></div>
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
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
              <AlertCircle className="h-12 w-12 text-yellow-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-neutral-800 mb-2">
                No Profile Found
              </h2>
              <p className="text-neutral-600 mb-4">
                Complete your profile to get personalized job matches
              </p>
              <button
                onClick={() => router.push('/profile/setup')}
                className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              >
                Complete Profile
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
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-neutral-800 mb-2">
                  My Profile
                </h1>
                <p className="text-neutral-600">
                  Manage your professional profile and preferences
                </p>
              </div>
              <button
                onClick={() => router.push('/profile/setup')}
                className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center space-x-2"
              >
                <Settings className="h-4 w-4" />
                <span>Edit Profile</span>
              </button>
            </div>
          </div>

          {/* Completion Status */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-neutral-800">
                Profile Completion
              </h2>
              <span className="text-2xl font-bold text-primary-600">
                {completionPercentage}%
              </span>
            </div>
            <div className="w-full bg-neutral-200 rounded-full h-3 mb-4">
              <div
                className="bg-primary-600 h-3 rounded-full transition-all duration-300"
                style={{ width: `${completionPercentage}%` }}
              />
            </div>
            {missingSections.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm font-medium text-yellow-800 mb-2">
                  Missing Sections:
                </p>
                <ul className="text-sm text-yellow-700 space-y-1">
                  {missingSections.map((section) => (
                    <li key={section} className="flex items-center space-x-2">
                      <span className="w-1.5 h-1.5 bg-yellow-600 rounded-full"></span>
                      <span>{section}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Career Targeting */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
            <div className="flex items-center space-x-3 mb-4">
              <User className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-neutral-800">
                Career Targeting
              </h2>
            </div>
            <div className="space-y-4">
              {/* Job Titles */}
              <div>
                <label className="text-sm font-medium text-neutral-600 mb-2 block">
                  Target Job Titles
                </label>
                {profile.primary_job_title || (profile.secondary_job_titles && profile.secondary_job_titles.length > 0) ? (
                  <div className="flex flex-wrap gap-2">
                    {profile.primary_job_title && (
                      <span className="inline-flex items-center px-3 py-1.5 bg-primary-100 text-primary-700 rounded-full text-sm font-medium">
                        {profile.primary_job_title}
                        <span className="ml-1 text-xs text-primary-600">(Primary)</span>
                      </span>
                    )}
                    {profile.secondary_job_titles && profile.secondary_job_titles.map((title, index) => (
                      <span
                        key={index}
                        className="px-3 py-1.5 bg-neutral-100 text-neutral-700 rounded-full text-sm font-medium"
                      >
                        {title}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-neutral-400">Not specified</p>
                )}
              </div>

              {/* Other info in grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-neutral-600">
                    Seniority Level
                  </label>
                  <p className="text-neutral-800 mt-1 capitalize">
                    {profile.seniority_level || <span className="text-neutral-400">Not specified</span>}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-neutral-600">
                    Work Preference
                  </label>
                  <p className="text-neutral-800 mt-1 capitalize">
                    {profile.work_preference || <span className="text-neutral-400">Not specified</span>}
                  </p>
                </div>
                {profile.desired_industries && profile.desired_industries.length > 0 && (
                  <div className="md:col-span-2">
                    <label className="text-sm font-medium text-neutral-600">
                      Desired Industries
                    </label>
                    <p className="text-neutral-800 mt-1">
                      {profile.desired_industries.join(', ')}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Skills */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
            <div className="flex items-center space-x-3 mb-4">
              <Award className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-neutral-800">
                Skills & Expertise
              </h2>
            </div>

            {/* Technical Skills */}
            {profile.technical_skills && profile.technical_skills.length > 0 && (
              <div className="mb-4">
                <label className="text-sm font-medium text-neutral-600 mb-2 block">
                  Technical Skills
                </label>
                <div className="flex flex-wrap gap-2">
                  {profile.technical_skills.map((skill, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm"
                    >
                      {skill.skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Soft Skills */}
            {profile.soft_skills && profile.soft_skills.length > 0 && (
              <div>
                <label className="text-sm font-medium text-neutral-600 mb-2 block">
                  Soft Skills
                </label>
                <div className="flex flex-wrap gap-2">
                  {profile.soft_skills.map((skill, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-accent-100 text-accent-700 rounded-full text-sm"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(!profile.technical_skills || profile.technical_skills.length === 0) &&
              (!profile.soft_skills || profile.soft_skills.length === 0) && (
                <p className="text-neutral-400">No skills added yet</p>
              )}
          </div>

          {/* Work Experience */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6 mb-6">
            <div className="flex items-center space-x-3 mb-4">
              <Briefcase className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-neutral-800">
                Work Experience
              </h2>
            </div>
            {profile.experience && profile.experience.length > 0 ? (
              <div className="space-y-4">
                {profile.experience.map((exp, index) => (
                  <div
                    key={index}
                    className="p-4 bg-neutral-50 rounded-lg border border-neutral-200"
                  >
                    <h3 className="font-semibold text-neutral-800">{exp.role}</h3>
                    <p className="text-sm text-neutral-600 mt-1">{exp.company}</p>
                    <p className="text-xs text-neutral-500 mt-1">{exp.duration}</p>
                    {exp.achievements && exp.achievements.length > 0 && (
                      <ul className="mt-3 space-y-1">
                        {exp.achievements.map((achievement, idx) => (
                          <li
                            key={idx}
                            className="text-sm text-neutral-700 flex items-start space-x-2"
                          >
                            <span className="text-primary-600 mt-1">•</span>
                            <span>{achievement}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-neutral-400">No work experience added yet</p>
            )}
          </div>

          {/* Preferences */}
          <div className="bg-white rounded-lg shadow-sm border border-neutral-200 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Settings className="h-5 w-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-neutral-800">
                Preferences
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-neutral-600">
                  Writing Tone
                </label>
                <p className="text-neutral-800 mt-1 capitalize">
                  {profile.writing_tone || <span className="text-neutral-400">Not specified</span>}
                </p>
              </div>
              {profile.ai_preferences && profile.ai_preferences.speed_vs_quality && (
                <div>
                  <label className="text-sm font-medium text-neutral-600">
                    AI Speed vs Quality
                  </label>
                  <p className="text-neutral-800 mt-1 capitalize">
                    {profile.ai_preferences.speed_vs_quality}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
