/**
 * Profile API Client
 * 
 * Functions for interacting with profile API endpoints.
 */

import { apiClient } from '../api/client'
import type { UserProfile, UserProfileFormData } from '@/types/profile'

/**
 * Get current user's profile
 */
export async function getMyProfile(): Promise<UserProfile> {
  return apiClient.get<UserProfile>('/api/v1/profiles/me')
}

/**
 * Create user profile
 */
export async function createProfile(data: UserProfileFormData): Promise<UserProfile> {
  return apiClient.post<UserProfile>('/api/v1/profiles', data)
}

/**
 * Update user profile
 */
export async function updateProfile(data: UserProfileFormData): Promise<UserProfile> {
  return apiClient.put<UserProfile>('/api/v1/profiles', data)
}

/**
 * Delete user profile
 */
export async function deleteProfile(): Promise<void> {
  return apiClient.delete<void>('/api/v1/profiles')
}

