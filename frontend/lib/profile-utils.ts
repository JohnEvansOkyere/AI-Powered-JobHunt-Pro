/**
 * Profile Utility Functions
 *
 * Utilities for profile completion calculation and validation.
 */

import type { UserProfile, UserProfileFormData } from '@/types/profile'

/**
 * Calculate profile completion percentage based on filled fields.
 *
 * Different fields have different weights:
 * - Essential fields (30%): primary_job_title, seniority_level, work_preference
 * - Skills (30%): technical_skills, soft_skills
 * - Experience (20%): experience
 * - Preferences (20%): writing_tone, ai_preferences, preferred_keywords
 */
export function calculateProfileCompletion(profile: UserProfile | UserProfileFormData | null): number {
  if (!profile) return 0

  let score = 0
  const weights = {
    // Essential career info (30%)
    primary_job_title: 10,
    seniority_level: 10,
    work_preference: 10,

    // Skills (30%)
    technical_skills: 20,
    soft_skills: 10,

    // Experience (20%)
    experience: 20,

    // Preferences (20%)
    writing_tone: 10,
    ai_preferences: 10,
  }

  // Check primary job title
  if (profile.primary_job_title && profile.primary_job_title.trim()) {
    score += weights.primary_job_title
  }

  // Check seniority level
  if (profile.seniority_level) {
    score += weights.seniority_level
  }

  // Check work preference
  if (profile.work_preference) {
    score += weights.work_preference
  }

  // Check technical skills
  if (profile.technical_skills && profile.technical_skills.length > 0) {
    score += weights.technical_skills
  }

  // Check soft skills
  if (profile.soft_skills && profile.soft_skills.length > 0) {
    score += weights.soft_skills
  }

  // Check experience
  if (profile.experience && profile.experience.length > 0) {
    // Check if at least one experience has all required fields
    const hasValidExperience = profile.experience.some(
      (exp) => exp.role && exp.company && exp.duration
    )
    if (hasValidExperience) {
      score += weights.experience
    }
  }

  // Check writing tone
  if (profile.writing_tone) {
    score += weights.writing_tone
  }

  // Check AI preferences
  if (profile.ai_preferences && profile.ai_preferences.speed_vs_quality) {
    score += weights.ai_preferences
  }

  return Math.min(100, Math.round(score))
}

/**
 * Get profile completion status message
 */
export function getCompletionMessage(percentage: number): string {
  if (percentage === 0) return 'Get started by filling out your profile'
  if (percentage < 30) return 'Just getting started - keep going!'
  if (percentage < 50) return 'Making progress - add more details'
  if (percentage < 80) return 'Almost there - a few more details'
  if (percentage < 100) return 'Looking good - complete the final touches'
  return 'Profile complete!'
}

/**
 * Get missing sections from profile
 */
export function getMissingSections(profile: UserProfile | UserProfileFormData | null): string[] {
  if (!profile) return ['All sections']

  const missing: string[] = []

  if (!profile.primary_job_title || !profile.seniority_level || !profile.work_preference) {
    missing.push('Career Targeting')
  }

  if (!profile.technical_skills || profile.technical_skills.length === 0) {
    missing.push('Technical Skills')
  }

  if (!profile.soft_skills || profile.soft_skills.length === 0) {
    missing.push('Soft Skills')
  }

  if (!profile.experience || profile.experience.length === 0) {
    missing.push('Work Experience')
  }

  if (!profile.writing_tone) {
    missing.push('Application Style')
  }

  if (!profile.ai_preferences || !profile.ai_preferences.speed_vs_quality) {
    missing.push('AI Preferences')
  }

  return missing
}
