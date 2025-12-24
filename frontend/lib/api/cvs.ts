/**
 * CV Management API Client
 * 
 * Functions for uploading, retrieving, and managing CVs.
 */

import { apiClient } from './client'

export interface CV {
  id: string
  user_id: string
  file_name: string
  file_path: string
  file_size: number | null
  file_type: string | null
  mime_type: string | null
  parsing_status: 'pending' | 'processing' | 'completed' | 'failed'
  parsing_error: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CVDetail extends CV {
  parsed_content: {
    personal_info?: {
      name?: string
      email?: string
      phone?: string
      location?: string
      linkedin?: string
      github?: string
      website?: string
    }
    summary?: string
    experience?: Array<{
      title: string
      company: string
      location?: string
      start_date?: string
      end_date?: string
      description?: string
      achievements?: string[]
    }>
    education?: Array<{
      degree: string
      institution: string
      location?: string
      graduation_date?: string
      gpa?: string
    }>
    skills?: {
      technical?: string[]
      languages?: string[]
      certifications?: string[]
    }
    projects?: Array<{
      name: string
      description?: string
      technologies?: string[]
      url?: string
    }>
  } | null
  raw_text: string | null
}

export interface UploadCVResponse {
  id: string
  user_id: string
  file_name: string
  file_path: string
  file_size: number | null
  file_type: string | null
  mime_type: string | null
  parsing_status: string
  parsing_error: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

/**
 * Upload a CV file (PDF or DOCX)
 */
export async function uploadCV(file: File): Promise<UploadCVResponse> {
  const formData = new FormData()
  formData.append('file', file)

  // Don't set Content-Type header - browser will set it automatically with boundary
  const response = await apiClient.post<UploadCVResponse>('/api/v1/cvs/upload', formData)

  // apiClient.post returns the JSON directly, not wrapped in data
  return response as UploadCVResponse
}

/**
 * Get all CVs for the current user
 */
export async function getCVs(): Promise<CV[]> {
  const response = await apiClient.get<CV[]>('/api/v1/cvs/')
  // apiClient.get returns the JSON directly, not wrapped in data
  return (response as any) || []
}

/**
 * Get the active CV for the current user
 */
export async function getActiveCV(): Promise<CVDetail | null> {
  const response = await apiClient.get<CVDetail | null>('/api/v1/cvs/active')
  // apiClient.get returns the JSON directly, not wrapped in data
  return (response as any) || null
}

/**
 * Get a specific CV by ID
 */
export async function getCV(cvId: string): Promise<CVDetail> {
  const response = await apiClient.get<CVDetail>(`/api/v1/cvs/${cvId}`)
  return response as CVDetail
}

/**
 * Activate a CV (sets it as active and deactivates others)
 */
export async function activateCV(cvId: string): Promise<CV> {
  const response = await apiClient.post<CV>(`/api/v1/cvs/${cvId}/activate`)
  return response as CV
}

/**
 * Delete a CV
 */
export async function deleteCV(cvId: string): Promise<void> {
  await apiClient.delete(`/api/v1/cvs/${cvId}`)
}

/**
 * Get a signed download URL for a CV
 */
export async function getCVDownloadURL(cvId: string): Promise<{ download_url: string }> {
  const response = await apiClient.get<{ download_url: string }>(
    `/api/v1/cvs/${cvId}/download-url`
  )
  return response as { download_url: string }
}

