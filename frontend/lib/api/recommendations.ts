/**
 * Recommendations V2 API client.
 *
 * Talks to GET /api/v1/recommendations (tiered, pre-computed).
 * See docs/RECOMMENDATIONS_V2_PLAN.md §5.7.
 */

import { apiClient } from './client'

export type Tier = 'tier1' | 'tier2' | 'tier3'

export interface RecommendedJob {
  id: string
  title: string
  company: string
  location: string | null
  remote_type: string | null
  job_type: string | null
  source: string | null
  job_link: string | null
  source_url: string | null
  posted_date: string | null
  scraped_at: string | null
}

export interface RecommendationItem {
  id: string
  job_id: string
  tier: Tier
  match_score: number         // 0..1
  match_reason: string | null
  semantic_fit: number | null
  title_alignment: number | null
  skill_overlap: number | null
  freshness: number | null
  llm_rerank_score: number | null
  expires_at: string
  job: RecommendedJob | null
}

export interface RecommendationsResponse {
  items: RecommendationItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  tier: Tier | null
}

/** Fetch one tier of recommendations. */
export async function fetchRecommendations(
  tier?: Tier,
  page = 1,
  pageSize = 20,
): Promise<RecommendationsResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (tier) params.set('tier', tier)
  return apiClient.get<RecommendationsResponse>(`/api/v1/recommendations?${params}`)
}

/** Trigger an on-demand re-run for the current user (rate-limited to 1/hr). */
export async function triggerRegenerate(): Promise<{ status: string; message: string }> {
  return apiClient.post('/api/v1/recommendations/regenerate')
}
