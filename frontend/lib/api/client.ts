/**
 * API Client for Backend Communication
 * 
 * Handles HTTP requests to the FastAPI backend.
 */

import { getCurrentSession } from '../auth'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl
  }

  private async getAuthToken(): Promise<string | null> {
    try {
      const session = await getCurrentSession()
      return session?.access_token || null
    } catch {
      return null
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const token = await this.getAuthToken()
    
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    }

    // Only set Content-Type for JSON, not for FormData
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: response.statusText,
      }))
      const errorMessage = error.detail || error.message || response.statusText || 'Request failed'
      const errorWithStatus = new Error(errorMessage)
      ;(errorWithStatus as any).status = response.status
      throw errorWithStatus
    }

    // Handle 204 No Content responses (no body to parse)
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return undefined as T
    }

    // Check if response has content
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      return response.json()
    }

    // If no content type or empty response, return undefined
    const text = await response.text()
    if (!text || text.trim() === '') {
      return undefined as T
    }

    // Try to parse as JSON
    try {
      return JSON.parse(text)
    } catch {
      return undefined as T
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, data?: unknown, options?: RequestInit): Promise<T> {
    const isFormData = data instanceof FormData
    const body = isFormData ? data : JSON.stringify(data)
    
    return this.request<T>(endpoint, {
      method: 'POST',
      body,
      ...options,
    })
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

// Export singleton instance
export const apiClient = new ApiClient()

