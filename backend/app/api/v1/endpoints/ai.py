"""
AI Usage and Statistics API Endpoints

Provides endpoints for viewing AI usage statistics and costs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from app.api.v1.dependencies import get_current_user
from app.services.ai_service import get_ai_service
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class UsageStatsResponse(BaseModel):
    """Usage statistics response model."""
    period_hours: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    cost_usd: float
    cost_by_provider: dict
    cost_by_task: dict
    total_cost_all_time: float


class ProviderStatsResponse(BaseModel):
    """Provider statistics response model."""
    provider: str
    requests: int
    successful: int
    failed: int
    cost: float
    input_tokens: int
    output_tokens: int
    total_tokens: int


@router.get("/usage", response_model=UsageStatsResponse)
def get_usage_stats(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get AI usage statistics.
    
    Returns:
        UsageStatsResponse: Usage statistics for the specified period
    """
    try:
        ai_service = get_ai_service()
        stats = ai_service.get_usage_stats(hours)
        return UsageStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage statistics: {str(e)}"
        )


@router.get("/usage/provider/{provider}", response_model=ProviderStatsResponse)
def get_provider_stats(
    provider: str,
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get statistics for a specific AI provider.
    
    Args:
        provider: Provider name (openai, gemini, groq, grok)
        hours: Number of hours to look back
        
    Returns:
        ProviderStatsResponse: Provider statistics
    """
    try:
        ai_service = get_ai_service()
        stats = ai_service.get_provider_stats(provider, hours)
        return ProviderStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting provider stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider statistics: {str(e)}"
        )

