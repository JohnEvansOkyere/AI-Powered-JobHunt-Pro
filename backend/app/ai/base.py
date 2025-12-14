"""
Base AI Provider Interface

Defines the common interface that all AI providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum


class TaskType(Enum):
    """Types of AI tasks."""
    JOB_MATCHING = "job_matching"
    CV_TAILORING = "cv_tailoring"
    COVER_LETTER = "cover_letter"
    EMAIL_DRAFTING = "email_drafting"
    JOB_ANALYSIS = "job_analysis"
    FAST_SUMMARY = "fast_summary"


class AIProvider(ABC):
    """Base class for AI providers."""

    def __init__(self, api_key: str, model_name: str):
        """
        Initialize AI provider.
        
        Args:
            api_key: API key for the provider
            model_name: Model name to use
        """
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            str: Generated text
        """
        pass

    @abstractmethod
    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Generate text with streaming response.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Yields:
            str: Text chunks
        """
        pass

    @property
    @abstractmethod
    def cost_per_token(self) -> Dict[str, float]:
        """
        Get cost per token (input/output).
        
        Returns:
            dict: {'input': float, 'output': float} in USD per 1K tokens
        """
        pass

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """Maximum tokens supported by the model."""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether the provider supports streaming."""
        pass

