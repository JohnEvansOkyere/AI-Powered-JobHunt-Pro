/**
 * External Jobs API Client
 * 
 * Functions for adding external job postings.
 */

import { apiClient } from './client'

export interface ExternalJobURLRequest {
  url: string
}

export interface ExternalJobTextRequest {
  text: string
  source_url?: string
}

export interface ExternalJobResponse {
  id: string
  title: string
  company: string
  location: string
  message: string
}

/**
 * Add a job posting from a URL
 */
export async function addJobFromURL(url: string): Promise<ExternalJobResponse> {
  return apiClient.post<ExternalJobResponse>('/api/v1/jobs/external/from-url', { url })
}

/**
 * Add a job posting from text
 */
export async function addJobFromText(
  text: string,
  source_url?: string
): Promise<ExternalJobResponse> {
  return apiClient.post<ExternalJobResponse>('/api/v1/jobs/external/from-text', {
    text,
    source_url,
  })
}
