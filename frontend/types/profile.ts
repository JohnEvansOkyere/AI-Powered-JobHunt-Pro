/**
 * User Profile TypeScript Types
 */

export interface TechnicalSkill {
  skill: string
  years?: number
  confidence?: number // 1-5 scale
}

export interface ExperienceItem {
  role: string
  company: string
  duration: string
  achievements: string[]
  metrics?: Record<string, any>
}

export interface AIPreferences {
  job_matching?: string
  cv_tailoring?: string
  cover_letter?: string
  email?: string
  speed_vs_quality?: 'speed' | 'quality' | 'balanced'
}

export interface UserProfile {
  id: string
  user_id: string
  // Career Targeting
  primary_job_title?: string
  secondary_job_titles?: string[]
  seniority_level?: 'entry' | 'mid' | 'senior' | 'lead' | 'executive'
  desired_industries?: string[]
  company_size_preference?: 'startup' | 'small' | 'medium' | 'large' | 'enterprise' | 'any'
  salary_range_min?: number
  salary_range_max?: number
  contract_type?: ('full-time' | 'contract' | 'freelance' | 'part-time')[]
  work_preference?: 'remote' | 'hybrid' | 'onsite' | 'flexible'
  // Skills & Tools
  technical_skills?: TechnicalSkill[]
  soft_skills?: string[]
  tools_technologies?: string[]
  // Experience
  experience?: ExperienceItem[]
  // Job Filtering
  preferred_keywords?: string[]
  excluded_keywords?: string[]
  blacklisted_companies?: string[]
  job_boards_include?: string[]
  job_boards_exclude?: string[]
  job_freshness_days?: number
  // Application Style
  writing_tone?: 'formal' | 'friendly' | 'confident' | 'professional'
  personal_branding_summary?: string
  first_person?: boolean
  email_length_preference?: 'short' | 'medium' | 'long'
  // Language & Localization
  preferred_language?: string
  local_job_market?: string
  // AI Preferences
  ai_preferences?: AIPreferences
  // Metadata
  created_at: string
  updated_at: string
}

export interface UserProfileFormData extends Partial<UserProfile> {}

