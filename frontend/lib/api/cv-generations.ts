import { apiClient } from './client'

export interface PersonalInfo {
  name: string
  email: string
  phone: string
  location: string
  linkedin: string
  github: string
  website: string
}

export interface Experience {
  title: string
  company: string
  location: string
  start_date: string
  end_date: string
  description: string
  achievements: string[]
}

export interface Education {
  degree: string
  institution: string
  location: string
  graduation_date: string
  gpa: string
}

export interface Skills {
  technical: string[]
  languages: string[]
  certifications: string[]
}

export interface Project {
  name: string
  description: string
  technologies: string[]
  url: string
}

export interface CVContent {
  personal_info: PersonalInfo
  summary: string
  experience: Experience[]
  education: Education[]
  skills: Skills
  projects: Project[]
}

export interface CVGeneration {
  id: string
  source_cv_id: string
  job_id: string
  revision: number
  content: CVContent
  validation_warnings: string[]
  prompt_version: string
  created_at: string
  updated_at: string
  job_title: string
  company: string
}

export interface CVRevision {
  revision: number
  change_source: 'ai' | 'user' | 'reset' | 'restore'
  created_at: string
}

export function createCVGeneration(jobId: string, regenerate = false) {
  return apiClient.post<CVGeneration>('/api/v1/cv-generations', {
    job_id: jobId,
    regenerate,
  })
}

export function getCVGeneration(id: string) {
  return apiClient.get<CVGeneration>(`/api/v1/cv-generations/${id}`)
}

export function saveCVGeneration(id: string, content: CVContent, expectedRevision: number) {
  return apiClient.patch<CVGeneration>(`/api/v1/cv-generations/${id}`, {
    content,
    expected_revision: expectedRevision,
  })
}

export function getCVRevisions(id: string) {
  return apiClient.get<CVRevision[]>(`/api/v1/cv-generations/${id}/revisions`)
}

export function restoreCVRevision(id: string, revision: number) {
  return apiClient.post<CVGeneration>(`/api/v1/cv-generations/${id}/restore/${revision}`)
}

export function resetCVGeneration(id: string) {
  return apiClient.post<CVGeneration>(`/api/v1/cv-generations/${id}/reset`)
}

export async function downloadCVGeneration(id: string, filename: string) {
  const blob = await apiClient.getBlob(`/api/v1/cv-generations/${id}/download.docx`)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
