"""
AI Usage Tracker

Tracks AI API usage, costs, and rate limiting.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class UsageRecord:
    """Record of a single AI API call."""
    task_type: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error: Optional[str] = None


class UsageTracker:
    """
    Tracks AI usage, costs, and enforces rate limits.
    
    Thread-safe for concurrent requests.
    """
    
    def __init__(self):
        """Initialize usage tracker."""
        self.records: list[UsageRecord] = []
        self.lock = Lock()
        
        # Rate limiting: requests per minute per user
        self.rate_limits: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.rate_limit_window = timedelta(minutes=1)
        
        # Cost tracking
        self.total_cost = 0.0
        self.cost_by_provider: Dict[str, float] = defaultdict(float)
        self.cost_by_task: Dict[str, float] = defaultdict(float)
    
    def record_usage(
        self,
        task_type: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        Record an AI API usage.
        
        Args:
            task_type: Type of task
            provider: Provider name
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            cost: Cost in USD
            success: Whether the call succeeded
            error: Error message if failed
        """
        with self.lock:
            record = UsageRecord(
                task_type=task_type,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                success=success,
                error=error
            )
            self.records.append(record)
            
            # Update cost tracking
            if success:
                self.total_cost += cost
                self.cost_by_provider[provider] += cost
                self.cost_by_task[task_type] += cost
            
            # Clean old records (keep last 24 hours)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self.records = [r for r in self.records if r.timestamp > cutoff]
    
    def check_rate_limit(self, user_id: str, provider: str, max_requests: int = 60) -> bool:
        """
        Check if user has exceeded rate limit for a provider.
        
        Args:
            user_id: User ID
            provider: Provider name
            max_requests: Maximum requests per minute
            
        Returns:
            bool: True if within limit, False if exceeded
        """
        with self.lock:
            now = datetime.utcnow()
            window_start = now - self.rate_limit_window
            
            # Count requests in current window
            key = f"{user_id}:{provider}"
            recent_requests = [
                r for r in self.records
                if r.timestamp > window_start
                and r.provider == provider
            ]
            
            # For now, we don't track per-user, so use global limit
            # TODO: Add user_id to UsageRecord for per-user tracking
            count = len(recent_requests)
            
            if count >= max_requests:
                logger.warning(f"Rate limit exceeded: {count} requests in last minute for {provider}")
                return False
            
            return True
    
    def get_usage_stats(self, hours: int = 24) -> Dict[str, any]:
        """
        Get usage statistics for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            dict: Usage statistics
        """
        with self.lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            recent_records = [r for r in self.records if r.timestamp > cutoff]
            
            total_requests = len(recent_records)
            successful_requests = sum(1 for r in recent_records if r.success)
            failed_requests = total_requests - successful_requests
            
            total_input_tokens = sum(r.input_tokens for r in recent_records)
            total_output_tokens = sum(r.output_tokens for r in recent_records)
            
            recent_cost = sum(r.cost for r in recent_records if r.success)
            
            return {
                "period_hours": hours,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "cost_usd": recent_cost,
                "cost_by_provider": dict(self.cost_by_provider),
                "cost_by_task": dict(self.cost_by_task),
                "total_cost_all_time": self.total_cost,
            }
    
    def get_provider_stats(self, provider: str, hours: int = 24) -> Dict[str, any]:
        """
        Get statistics for a specific provider.
        
        Args:
            provider: Provider name
            hours: Number of hours to look back
            
        Returns:
            dict: Provider statistics
        """
        with self.lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            provider_records = [
                r for r in self.records
                if r.provider == provider and r.timestamp > cutoff
            ]
            
            if not provider_records:
                return {
                    "provider": provider,
                    "requests": 0,
                    "cost": 0.0,
                    "tokens": 0,
                }
            
            return {
                "provider": provider,
                "requests": len(provider_records),
                "successful": sum(1 for r in provider_records if r.success),
                "failed": sum(1 for r in provider_records if not r.success),
                "cost": sum(r.cost for r in provider_records if r.success),
                "input_tokens": sum(r.input_tokens for r in provider_records),
                "output_tokens": sum(r.output_tokens for r in provider_records),
                "total_tokens": sum(r.input_tokens + r.output_tokens for r in provider_records),
            }


# Global usage tracker instance
_usage_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get or create the global usage tracker instance."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker

