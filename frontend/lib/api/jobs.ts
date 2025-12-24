/**
 * Job Management API Client
 * 
 * Functions for searching, filtering, and managing jobs.
 */

import { apiClient } from './client'

export interface Job {
  id: string
  title: string
  company: string
  location: string | null
  description: string
  job_link: string
  source: string
  source_id: string | null
  posted_date: string | null
  scraped_at: string
  normalized_title: string | null
  normalized_location: string | null
  salary_range: string | null
  job_type: string | null
  remote_type: string | null
  processing_status: string
  created_at: string
  updated_at: string
  match_score?: number | null  // Relevance score (0-100)
  match_reasons?: string[] | null  // Match reasons
}

export interface JobSearchParams {
  q?: string
  source?: string
  location?: string
  job_type?: string
  remote_type?: string
  min_posted_days?: number
  matched?: boolean  // Return only matched jobs with scores
  page?: number
  page_size?: number
}

export interface JobSearchResponse {
  jobs: Job[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ScrapeJobsRequest {
  sources: string[]
  keywords?: string[]
  location?: string
  max_results_per_source?: number
}

export interface ScrapeJobsResponse {
  scraping_job_id: string
  status: string
  message: string
}

export interface ScrapingJob {
  id: string
  user_id: string | null
  sources: string[]
  keywords: string[] | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  jobs_found: number
  jobs_processed: number
  error_message: string | null
  result_summary: {
    total_found?: number
    stored?: number
    duplicates?: number
    sources?: string[]
  } | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

/**
 * Search and filter jobs
 */
export async function searchJobs(params: JobSearchParams = {}): Promise<JobSearchResponse> {
  const queryParams = new URLSearchParams()
  
  if (params.q) queryParams.append('q', params.q)
  if (params.source) queryParams.append('source', params.source)
  if (params.location) queryParams.append('location', params.location)
  if (params.job_type) queryParams.append('job_type', params.job_type)
  if (params.remote_type) queryParams.append('remote_type', params.remote_type)
  if (params.min_posted_days) queryParams.append('min_posted_days', params.min_posted_days.toString())
  if (params.matched !== undefined) queryParams.append('matched', params.matched.toString())
  if (params.page) queryParams.append('page', params.page.toString())
  if (params.page_size) queryParams.append('page_size', params.page_size.toString())
  
  const queryString = queryParams.toString()
  const endpoint = `/api/v1/jobs/${queryString ? `?${queryString}` : ''}`
  
  return apiClient.get<JobSearchResponse>(endpoint) as Promise<JobSearchResponse>
}

/**
 * Get a specific job by ID
 */
export async function getJob(jobId: string): Promise<Job> {
  return apiClient.get<Job>(`/api/v1/jobs/${jobId}`) as Promise<Job>
}

/**
 * Get available scraping sources
 */
export async function getAvailableSources(): Promise<string[]> {
  return apiClient.get<string[]>('/api/v1/jobs/sources/available') as Promise<string[]>
}

/**
 * Start a job scraping task
 */
export async function startScraping(request: ScrapeJobsRequest): Promise<ScrapeJobsResponse> {
  return apiClient.post<ScrapeJobsResponse>('/api/v1/jobs/scrape', request) as Promise<ScrapeJobsResponse>
}

/**
 * Get scraping job status
 */
export async function getScrapingJob(scrapingJobId: string): Promise<ScrapingJob> {
  return apiClient.get<ScrapingJob>(`/api/v1/jobs/scraping/${scrapingJobId}`) as Promise<ScrapingJob>
}

/**
 * List user's scraping jobs
 */
export async function listScrapingJobs(status?: string): Promise<ScrapingJob[]> {
  const endpoint = status 
    ? `/api/v1/jobs/scraping/?status_filter=${status}`
    : '/api/v1/jobs/scraping/'
  return apiClient.get<ScrapingJob[]>(endpoint) as Promise<ScrapingJob[]>
}

