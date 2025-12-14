/**
 * Multi-Step Profile Form Component
 * 
 * Comprehensive profile form with multiple steps for all profile sections.
 */

'use client'

import { useState } from 'react'
import { useProfile } from '@/hooks/useProfile'
import type { UserProfileFormData } from '@/types/profile'

interface ProfileFormProps {
  onComplete?: () => void
}

export function ProfileForm({ onComplete }: ProfileFormProps) {
  const { saveProfile, saving } = useProfile()
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<UserProfileFormData>({})

  const totalSteps = 6

  const updateFormData = (data: Partial<UserProfileFormData>) => {
    setFormData((prev) => ({ ...prev, ...data }))
  }

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSubmit = async () => {
    try {
      await saveProfile(formData)
      onComplete?.()
    } catch (error) {
      // Error handling is done in useProfile hook
    }
  }

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6">
      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-neutral-700">
            Step {currentStep} of {totalSteps}
          </span>
          <span className="text-sm text-neutral-500">
            {Math.round((currentStep / totalSteps) * 100)}% Complete
          </span>
        </div>
        <div className="w-full bg-neutral-200 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(currentStep / totalSteps) * 100}%` }}
          />
        </div>
      </div>

      {/* Step Content */}
      <div className="min-h-[400px]">
        {currentStep === 1 && (
          <CareerTargetingStep
            data={formData}
            onChange={updateFormData}
          />
        )}
        {currentStep === 2 && (
          <SkillsStep
            data={formData}
            onChange={updateFormData}
          />
        )}
        {currentStep === 3 && (
          <ExperienceStep
            data={formData}
            onChange={updateFormData}
          />
        )}
        {currentStep === 4 && (
          <JobPreferencesStep
            data={formData}
            onChange={updateFormData}
          />
        )}
        {currentStep === 5 && (
          <ApplicationStyleStep
            data={formData}
            onChange={updateFormData}
          />
        )}
        {currentStep === 6 && (
          <AIPreferencesStep
            data={formData}
            onChange={updateFormData}
          />
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-8 pt-6 border-t border-neutral-200">
        <button
          type="button"
          onClick={handlePrevious}
          disabled={currentStep === 1}
          className="px-4 py-2 text-sm font-medium text-neutral-700 bg-white border border-neutral-300 rounded-lg hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>

        {currentStep < totalSteps ? (
          <button
            type="button"
            onClick={handleNext}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-700 rounded-lg hover:bg-primary-800"
          >
            Next
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving}
            className="px-6 py-2 text-sm font-medium text-white bg-accent-600 rounded-lg hover:bg-accent-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Complete Profile'}
          </button>
        )}
      </div>
    </div>
  )
}

// Step Components (simplified - will be expanded)
function CareerTargetingStep({
  data,
  onChange,
}: {
  data: UserProfileFormData
  onChange: (data: Partial<UserProfileFormData>) => void
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">Career Targeting</h2>
      <p className="text-neutral-600">Tell us about your career goals and preferences.</p>
      
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Primary Job Title
        </label>
        <input
          type="text"
          value={data.primary_job_title || ''}
          onChange={(e) => onChange({ primary_job_title: e.target.value })}
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
          placeholder="e.g., Software Engineer"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Seniority Level
        </label>
        <select
          value={data.seniority_level || ''}
          onChange={(e) => onChange({ seniority_level: e.target.value })}
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="">Select level</option>
          <option value="entry">Entry Level</option>
          <option value="mid">Mid Level</option>
          <option value="senior">Senior</option>
          <option value="lead">Lead</option>
          <option value="executive">Executive</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Work Preference
        </label>
        <select
          value={data.work_preference || ''}
          onChange={(e) => onChange({ work_preference: e.target.value })}
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="">Select preference</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="onsite">Onsite</option>
          <option value="flexible">Flexible</option>
        </select>
      </div>
    </div>
  )
}

function SkillsStep({
  data,
  onChange,
}: {
  data: UserProfileFormData
  onChange: (data: Partial<UserProfileFormData>) => void
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">Skills & Tools</h2>
      <p className="text-neutral-600">Add your technical skills, soft skills, and tools.</p>
      
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Soft Skills (comma-separated)
        </label>
        <input
          type="text"
          value={data.soft_skills?.join(', ') || ''}
          onChange={(e) =>
            onChange({
              soft_skills: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
            })
          }
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
          placeholder="e.g., Communication, Leadership, Problem-solving"
        />
      </div>
    </div>
  )
}

function ExperienceStep({
  data,
  onChange,
}: {
  data: UserProfileFormData
  onChange: (data: Partial<UserProfileFormData>) => void
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">Work Experience</h2>
      <p className="text-neutral-600">Add your professional experience.</p>
      <p className="text-sm text-neutral-500">Experience editing will be available after profile creation.</p>
    </div>
  )
}

function JobPreferencesStep({
  data,
  onChange,
}: {
  data: UserProfileFormData
  onChange: (data: Partial<UserProfileFormData>) => void
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">Job Preferences</h2>
      <p className="text-neutral-600">Customize how we match jobs for you.</p>
      
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Preferred Keywords (comma-separated)
        </label>
        <input
          type="text"
          value={data.preferred_keywords?.join(', ') || ''}
          onChange={(e) =>
            onChange({
              preferred_keywords: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
            })
          }
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
          placeholder="e.g., Python, React, AWS"
        />
      </div>
    </div>
  )
}

function ApplicationStyleStep({
  data,
  onChange,
}: {
  data: UserProfileFormData
  onChange: (data: Partial<UserProfileFormData>) => void
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">Application Style</h2>
      <p className="text-neutral-600">Customize how your applications are written.</p>
      
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Writing Tone
        </label>
        <select
          value={data.writing_tone || 'professional'}
          onChange={(e) => onChange({ writing_tone: e.target.value })}
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="formal">Formal</option>
          <option value="professional">Professional</option>
          <option value="friendly">Friendly</option>
          <option value="confident">Confident</option>
        </select>
      </div>
    </div>
  )
}

function AIPreferencesStep({
  data,
  onChange,
}: {
  data: UserProfileFormData
  onChange: (data: Partial<UserProfileFormData>) => void
}) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">AI Preferences</h2>
      <p className="text-neutral-600">Choose which AI models to use for different tasks.</p>
      
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Speed vs Quality
        </label>
        <select
          value={data.ai_preferences?.speed_vs_quality || 'balanced'}
          onChange={(e) =>
            onChange({
              ai_preferences: {
                ...data.ai_preferences,
                speed_vs_quality: e.target.value,
              },
            })
          }
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="speed">Speed (Faster, Lower Cost)</option>
          <option value="balanced">Balanced</option>
          <option value="quality">Quality (Slower, Higher Cost)</option>
        </select>
      </div>
    </div>
  )
}

