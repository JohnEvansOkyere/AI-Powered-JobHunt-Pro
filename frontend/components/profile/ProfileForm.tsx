/**
 * Multi-Step Profile Form Component
 * 
 * Comprehensive profile form with multiple steps for all profile sections.
 */

'use client'

import { useState, useEffect } from 'react'
import { useProfile } from '@/hooks/useProfile'
import type { UserProfileFormData } from '@/types/profile'
import { SKILL_CATEGORIES, searchSkills } from '@/lib/skills'
import { calculateProfileCompletion } from '@/lib/profile-utils'

interface ProfileFormProps {
  onComplete?: () => void
}

export function ProfileForm({ onComplete }: ProfileFormProps) {
  const { profile, saveProfile, saving } = useProfile()
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<UserProfileFormData>({})

  const totalSteps = 5

  // Load existing profile data when available
  useEffect(() => {
    if (profile) {
      setFormData({
        primary_job_title: profile.primary_job_title,
        secondary_job_titles: profile.secondary_job_titles,
        seniority_level: profile.seniority_level,
        work_preference: profile.work_preference,
        technical_skills: profile.technical_skills,
        soft_skills: profile.soft_skills,
        tools_technologies: profile.tools_technologies,
        experience: profile.experience,
        preferred_keywords: profile.preferred_keywords,
        writing_tone: profile.writing_tone,
        ai_preferences: profile.ai_preferences,
        desired_industries: profile.desired_industries,
      })
    }
  }, [profile])

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

  // Calculate actual completion percentage based on filled data
  const completionPercentage = calculateProfileCompletion(formData)

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6">
      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-neutral-700">
            Step {currentStep} of {totalSteps}
          </span>
          <span className="text-sm font-medium text-primary-600">
            {completionPercentage}% Complete
          </span>
        </div>
        <div className="w-full bg-neutral-200 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${completionPercentage}%` }}
          />
        </div>
        {completionPercentage < 100 && (
          <p className="text-xs text-neutral-500 mt-2">
            Fill in more details to increase your match quality
          </p>
        )}
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
          <ApplicationStyleStep
            data={formData}
            onChange={updateFormData}
          />
        )}
        {currentStep === 5 && (
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
  const [jobTitleInput, setJobTitleInput] = useState('')
  const [allJobTitles, setAllJobTitles] = useState<string[]>([])

  // Initialize job titles from data
  useEffect(() => {
    const titles: string[] = []
    if (data.primary_job_title) {
      titles.push(data.primary_job_title)
    }
    if (data.secondary_job_titles && data.secondary_job_titles.length > 0) {
      titles.push(...data.secondary_job_titles)
    }
    setAllJobTitles(titles)
  }, [data.primary_job_title, data.secondary_job_titles])

  const handleAddJobTitle = () => {
    const trimmedTitle = jobTitleInput.trim()
    if (!trimmedTitle) return

    // Split by comma if user entered multiple at once
    const newTitles = trimmedTitle
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
      .filter((t) => !allJobTitles.includes(t))

    if (newTitles.length === 0) {
      setJobTitleInput('')
      return
    }

    const updatedTitles = [...allJobTitles, ...newTitles]
    setAllJobTitles(updatedTitles)

    // First title is primary, rest are secondary
    onChange({
      primary_job_title: updatedTitles[0],
      secondary_job_titles: updatedTitles.slice(1),
    })

    setJobTitleInput('')
  }

  const handleRemoveJobTitle = (titleToRemove: string) => {
    const updatedTitles = allJobTitles.filter((t) => t !== titleToRemove)
    setAllJobTitles(updatedTitles)

    // First title is primary, rest are secondary
    onChange({
      primary_job_title: updatedTitles[0] || '',
      secondary_job_titles: updatedTitles.slice(1),
    })
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleAddJobTitle()
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">Career Targeting</h2>
      <p className="text-neutral-600">Tell us about your career goals and preferences.</p>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Job Titles (Target Roles)
        </label>

        {/* Display existing job titles */}
        {allJobTitles.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {allJobTitles.map((title, index) => (
              <span
                key={index}
                className="inline-flex items-center px-3 py-1.5 bg-primary-100 text-primary-700 rounded-full text-sm font-medium"
              >
                {title}
                {index === 0 && (
                  <span className="ml-1 text-xs text-primary-600">(Primary)</span>
                )}
                <button
                  type="button"
                  onClick={() => handleRemoveJobTitle(title)}
                  className="ml-2 text-primary-600 hover:text-primary-800 focus:outline-none"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Input for adding new job titles */}
        <div className="flex gap-2">
          <input
            type="text"
            value={jobTitleInput}
            onChange={(e) => setJobTitleInput(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1 px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
            placeholder="e.g., Data Scientist, ML Engineer, AI Engineer"
          />
          <button
            type="button"
            onClick={handleAddJobTitle}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Add
          </button>
        </div>
        <p className="text-xs text-neutral-500 mt-2">
          Add multiple job titles separated by commas, or add them one at a time. The first title will be your primary role.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Seniority Level
        </label>
        <select
          value={data.seniority_level || ''}
          onChange={(e) => onChange({ seniority_level: e.target.value as 'entry' | 'mid' | 'senior' | 'lead' | 'executive' })}
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
          onChange={(e) => onChange({ work_preference: e.target.value as 'remote' | 'hybrid' | 'onsite' | 'flexible' })}
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
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [skillSearchQuery, setSkillSearchQuery] = useState('')
  const [showSkillDropdown, setShowSkillDropdown] = useState(false)
  const [categorySkills, setCategorySkills] = useState<Record<string, string[]>>({})
  const [softSkillsInput, setSoftSkillsInput] = useState(
    data.soft_skills?.join(', ') || ''
  )

  // Initialize category skills from existing technical_skills
  useEffect(() => {
    const existingSkills = data.technical_skills || []
    const skillsByCategory: Record<string, string[]> = {}
    
    SKILL_CATEGORIES.forEach((category) => {
      skillsByCategory[category.id] = []
    })
    
    existingSkills.forEach((skillItem) => {
      // Try to find which category this skill belongs to
      const category = SKILL_CATEGORIES.find((cat) =>
        cat.skills.includes(skillItem.skill)
      )
      if (category) {
        if (!skillsByCategory[category.id]) {
          skillsByCategory[category.id] = []
        }
        skillsByCategory[category.id].push(skillItem.skill)
      }
    })
    
    setCategorySkills(skillsByCategory)
  }, [data.technical_skills])

  useEffect(() => {
    setSoftSkillsInput(data.soft_skills?.join(', ') || '')
  }, [data.soft_skills])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest('.skill-dropdown-container')) {
        setShowSkillDropdown(false)
      }
    }

    if (showSkillDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showSkillDropdown])

  const handleCategorySelect = (categoryId: string) => {
    setSelectedCategory(categoryId)
    setSkillSearchQuery('')
    setShowSkillDropdown(true)
  }

  const handleSkillAdd = (skill: string) => {
    if (!selectedCategory) return
    
    const currentSkills = categorySkills[selectedCategory] || []
    if (currentSkills.includes(skill)) return
    
    const updated = {
      ...categorySkills,
      [selectedCategory]: [...currentSkills, skill],
    }
    setCategorySkills(updated)
    
    // Update technical_skills in form data
    const existingSkillsMap = new Map(
      (data.technical_skills || []).map((s) => [s.skill, s])
    )

    const allTechnicalSkills = Object.values(updated)
      .flat()
      .map((skillName) => {
        const existing = existingSkillsMap.get(skillName)
        return {
          skill: skillName,
          years: existing?.years,
          confidence: existing?.confidence,
        }
      })

    onChange({ technical_skills: allTechnicalSkills })
    setSkillSearchQuery('')
  }

  const handleSkillRemove = (categoryId: string, skill: string) => {
    const currentSkills = categorySkills[categoryId] || []
    const updated = {
      ...categorySkills,
      [categoryId]: currentSkills.filter((s) => s !== skill),
    }
    setCategorySkills(updated)
    
    // Update technical_skills
    const existingSkillsMap = new Map(
      (data.technical_skills || []).map((s) => [s.skill, s])
    )

    const allTechnicalSkills = Object.values(updated)
      .flat()
      .map((skillName) => {
        const existing = existingSkillsMap.get(skillName)
        return {
          skill: skillName,
          years: existing?.years,
          confidence: existing?.confidence,
        }
      })

    onChange({ technical_skills: allTechnicalSkills })
  }

  const handleCustomSkillAdd = (categoryId: string, skillInput: string) => {
    const skills = skillInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    
    if (skills.length === 0) return
    
    const currentSkills = categorySkills[categoryId] || []
    const newSkills = [...new Set([...currentSkills, ...skills])]
    
    const updated = {
      ...categorySkills,
      [categoryId]: newSkills,
    }
    setCategorySkills(updated)
    
    // Update technical_skills
    const existingSkillsMap = new Map(
      (data.technical_skills || []).map((s) => [s.skill, s])
    )

    const allTechnicalSkills = Object.values(updated)
      .flat()
      .map((skillName) => {
        const existing = existingSkillsMap.get(skillName)
        return {
          skill: skillName,
          years: existing?.years,
          confidence: existing?.confidence,
        }
      })

    onChange({ technical_skills: allTechnicalSkills })
  }

  const handleSoftSkillsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSoftSkillsInput(value)

    // Split by comma, trim each skill, and filter out empty/whitespace-only entries
    const skills = value
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0)

    onChange({
      soft_skills: skills,
    })
  }

  const filteredSkills = skillSearchQuery
    ? searchSkills(skillSearchQuery, 10)
    : selectedCategory
    ? SKILL_CATEGORIES.find((c) => c.id === selectedCategory)?.skills.slice(0, 20) || []
    : []

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">Skills & Expertise</h2>
      <p className="text-neutral-600">
        Add your technical skills organized by category. Separate multiple skills with commas.
      </p>

      {/* Category Selection */}
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Select Category
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {SKILL_CATEGORIES.map((category) => {
            const skillCount = categorySkills[category.id]?.length || 0
            return (
              <button
                key={category.id}
                type="button"
                onClick={() => handleCategorySelect(category.id)}
                className={`px-4 py-3 text-left border rounded-lg transition-colors ${
                  selectedCategory === category.id
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-neutral-300 hover:border-primary-300 hover:bg-neutral-50'
                }`}
              >
                <div className="font-medium">{category.name}</div>
                {skillCount > 0 && (
                  <div className="text-xs text-neutral-500 mt-1">
                    {skillCount} skill{skillCount !== 1 ? 's' : ''}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Skill Selection for Selected Category */}
      {selectedCategory && (
        <div className="space-y-4 p-4 bg-neutral-50 rounded-lg border border-neutral-200">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-neutral-800">
              {SKILL_CATEGORIES.find((c) => c.id === selectedCategory)?.name}
            </h3>
            <button
              type="button"
              onClick={() => {
                setSelectedCategory(null)
                setSkillSearchQuery('')
                setShowSkillDropdown(false)
              }}
              className="text-sm text-neutral-500 hover:text-neutral-700"
            >
              Close
            </button>
          </div>

          {/* Search Skills */}
          <div className="relative skill-dropdown-container">
            <input
              type="text"
              value={skillSearchQuery}
              onChange={(e) => {
                setSkillSearchQuery(e.target.value)
                setShowSkillDropdown(true)
              }}
              onFocus={() => setShowSkillDropdown(true)}
              placeholder="Search or type skills (comma-separated)..."
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
            />
            
            {/* Skill Dropdown */}
            {showSkillDropdown && filteredSkills.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-neutral-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {filteredSkills.map((skill) => {
                  const isSelected = categorySkills[selectedCategory]?.includes(skill)
                  return (
                    <button
                      key={skill}
                      type="button"
                      onClick={() => {
                        if (!isSelected) {
                          handleSkillAdd(skill)
                        }
                        setShowSkillDropdown(false)
                      }}
                      disabled={isSelected}
                      className={`w-full px-4 py-2 text-left hover:bg-neutral-50 ${
                        isSelected
                          ? 'bg-primary-50 text-primary-700 cursor-not-allowed'
                          : 'text-neutral-800'
                      }`}
                    >
                      {skill}
                      {isSelected && (
                        <span className="ml-2 text-xs text-primary-600">✓ Added</span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Custom Skills Input */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Add Custom Skills (comma-separated)
            </label>
            <input
              type="text"
              placeholder="e.g., Custom Skill 1, Custom Skill 2"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleCustomSkillAdd(selectedCategory, e.currentTarget.value)
                  e.currentTarget.value = ''
                }
              }}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
            />
            <p className="text-xs text-neutral-500 mt-1">
              Press Enter to add skills, separate multiple skills with commas
            </p>
          </div>

          {/* Selected Skills for Category */}
          {categorySkills[selectedCategory] && categorySkills[selectedCategory].length > 0 && (
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Your Skills ({categorySkills[selectedCategory].length})
              </label>
              <div className="flex flex-wrap gap-2">
                {categorySkills[selectedCategory].map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm"
                  >
                    {skill}
                    <button
                      type="button"
                      onClick={() => handleSkillRemove(selectedCategory, skill)}
                      className="ml-2 text-primary-600 hover:text-primary-800"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Soft Skills */}
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          Soft Skills (comma-separated)
        </label>
        <input
          type="text"
          value={softSkillsInput}
          onChange={handleSoftSkillsChange}
          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
          placeholder="e.g., Communication, Leadership, Problem-solving"
        />
        <p className="text-xs text-neutral-500 mt-1">
          Separate multiple skills with commas
        </p>
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
  const [experiences, setExperiences] = useState(
    data.experience || []
  )
  // Local state to preserve raw input for responsibilities
  const [responsibilitiesInputs, setResponsibilitiesInputs] = useState<Record<number, string>>({})

  useEffect(() => {
    const updated = data.experience || []
    setExperiences(updated)
    
    // Initialize local state for responsibilities inputs only if not already set
    // This prevents overwriting user input while typing
    setResponsibilitiesInputs((prev) => {
      const inputs: Record<number, string> = { ...prev }
      updated.forEach((exp, index) => {
        // Only initialize if not already in state (preserves user input)
        if (!(index in inputs)) {
          inputs[index] = exp.achievements?.join(', ') || ''
        }
      })
      return inputs
    })
  }, [data.experience])

  const handleAddExperience = () => {
    const newExperience = {
      role: '',
      company: '',
      duration: '',
      achievements: [],
    }
    const newIndex = experiences.length
    const updated = [...experiences, newExperience]
    setExperiences(updated)
    
    // Add empty input for new experience
    setResponsibilitiesInputs((prev) => ({
      ...prev,
      [newIndex]: '',
    }))
    
    onChange({ experience: updated })
  }

  const handleRemoveExperience = (index: number) => {
    const updated = experiences.filter((_, i) => i !== index)
    setExperiences(updated)
    
    // Remove input state for deleted experience and reindex
    // Preserve existing input values where possible
    const newInputs: Record<number, string> = {}
    updated.forEach((exp, i) => {
      // Try to preserve input from previous index if it exists
      const prevIndex = i < index ? i : i + 1
      if (responsibilitiesInputs[prevIndex] !== undefined) {
        newInputs[i] = responsibilitiesInputs[prevIndex]
      } else {
        newInputs[i] = exp.achievements?.join(', ') || ''
      }
    })
    setResponsibilitiesInputs(newInputs)
    
    onChange({ experience: updated })
  }

  const handleExperienceChange = (
    index: number,
    field: 'role' | 'company' | 'duration',
    value: string
  ) => {
    const updated = experiences.map((exp, i) => {
      if (i === index) {
        return { ...exp, [field]: value }
      }
      return exp
    })
    setExperiences(updated)
    onChange({ experience: updated })
  }

  const handleResponsibilitiesChange = (index: number, value: string) => {
    // Update local input state immediately using functional update
    setResponsibilitiesInputs((prev) => ({
      ...prev,
      [index]: value,
    }))
    
    // Parse and update form data in the background
    const responsibilities = value
      .split(',')
      .map((r) => r.trim())
      .filter(Boolean)
    
    // Use functional update for experiences too
    setExperiences((prev) => {
      const updated = prev.map((exp, i) => {
        if (i === index) {
          return { ...exp, achievements: responsibilities }
        }
        return exp
      })
      onChange({ experience: updated })
      return updated
    })
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-neutral-800">Work Experience</h2>
      <p className="text-neutral-600">Add your professional experience.</p>

      <div className="space-y-6">
        {experiences.map((exp, index) => (
          <div
            key={index}
            className="p-6 border border-neutral-300 rounded-lg bg-neutral-50"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-neutral-800">
                Experience {index + 1}
              </h3>
              {experiences.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemoveExperience(index)}
                  className="text-sm text-red-600 hover:text-red-700 font-medium"
                >
                  Remove
                </button>
              )}
            </div>

            <div className="space-y-4">
              {/* Company Name */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Company Name *
                </label>
                <input
                  type="text"
                  value={exp.company || ''}
                  onChange={(e) =>
                    handleExperienceChange(index, 'company', e.target.value)
                  }
                  placeholder="e.g., Google, Microsoft, Amazon"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  required
                />
              </div>

              {/* Role/Job Title */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Role/Job Title *
                </label>
                <input
                  type="text"
                  value={exp.role || ''}
                  onChange={(e) =>
                    handleExperienceChange(index, 'role', e.target.value)
                  }
                  placeholder="e.g., Software Engineer, Product Manager"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  required
                />
              </div>

              {/* Duration */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Duration *
                </label>
                <input
                  type="text"
                  value={exp.duration || ''}
                  onChange={(e) =>
                    handleExperienceChange(index, 'duration', e.target.value)
                  }
                  placeholder="e.g., Jan 2020 - Present, 2020-2023"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  required
                />
              </div>

              {/* Responsibilities */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Responsibilities (comma-separated)
                </label>
                <textarea
                  value={responsibilitiesInputs[index] || ''}
                  onChange={(e) =>
                    handleResponsibilitiesChange(index, e.target.value)
                  }
                  placeholder="e.g., Led development of new features, Managed team of 5 engineers, Improved system performance by 40%"
                  rows={4}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                />
                <p className="text-xs text-neutral-500 mt-1">
                  Separate multiple responsibilities with commas
                </p>
              </div>
            </div>
          </div>
        ))}

        {/* Add More Experience Button */}
        <button
          type="button"
          onClick={handleAddExperience}
          className="w-full py-3 border-2 border-dashed border-neutral-300 rounded-lg text-neutral-600 hover:border-primary-400 hover:text-primary-600 hover:bg-primary-50 transition-colors font-medium"
        >
          + Add Another Experience
        </button>

        {experiences.length === 0 && (
          <div className="text-center py-8 text-neutral-500">
            <p>No work experience added yet.</p>
            <p className="text-sm mt-2">Click "Add Another Experience" to get started.</p>
          </div>
        )}
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
          onChange={(e) => onChange({ writing_tone: e.target.value as 'formal' | 'friendly' | 'confident' | 'professional' })}
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
                speed_vs_quality: e.target.value as 'speed' | 'quality' | 'balanced',
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

