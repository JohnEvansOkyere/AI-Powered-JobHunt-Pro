/**
 * API Client for Backend Communication
 * 
 * Handles HTTP requests to the FastAPI backend.
 */

import { getCurrentSession, signOut } from '../auth'
import { apiError, connectionError, errorFields, UserFacingError } from '../errors'

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

  private async handleAuthFailure(response: Response, message: string) {
    if (response.status !== 401 && response.status !== 403) {
      return
    }

    if (
      message === 'Email verification required' ||
      message === 'Invalid authentication credentials' ||
      message === 'Could not validate credentials' ||
      message === 'Account is not available' ||
      message.startsWith('Your account has been suspended')
    ) {
      try {
        await signOut()
      } catch {
        // Ignore sign-out cleanup failures here; the original auth error still matters most.
      }
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

    let response: Response
    try {
      response = await fetch(url, { ...options, headers })
    } catch {
      throw connectionError()
    }

    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null)
      await this.handleAuthFailure(response, errorFields(body).message || '')
      throw apiError(response, body)
    }

    // Handle 204 No Content responses (no body to parse)
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return undefined as T
    }

    try {
      const text = await response.text()
      if (!text.trim()) return undefined as T
      return JSON.parse(text)
    } catch {
      throw new UserFacingError('We could not read the response. Please try again.', response.status)
    }
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async getBlob(endpoint: string): Promise<Blob> {
    const token = await this.getAuthToken()
    const headers: Record<string, string> = {}
    if (token) headers.Authorization = `Bearer ${token}`
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}${endpoint}`, { headers })
    } catch {
      throw connectionError()
    }
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null)
      await this.handleAuthFailure(response, errorFields(body).message || '')
      throw apiError(response, body)
    }
    try {
      return await response.blob()
    } catch {
      throw connectionError()
    }
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
