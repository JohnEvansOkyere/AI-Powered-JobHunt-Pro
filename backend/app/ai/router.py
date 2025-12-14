"""
AI Model Router

Intelligently routes AI requests to appropriate providers based on:
- Task type
- User preferences
- Provider availability
- Cost optimization
- Fallback handling
"""

from typing import Optional, Dict, Any
from enum import Enum

from app.ai.base import AIProvider, TaskType
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.grok_provider import GrokProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.groq_provider import GroqProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelRouter:
    """
    Routes AI requests to appropriate providers with fallback support.
    """

    # Default model mapping by task type
    DEFAULT_MODELS: Dict[TaskType, str] = {
        TaskType.JOB_ANALYSIS: "gemini",  # Gemini for analysis
        TaskType.CV_TAILORING: "openai",  # OpenAI for CV tailoring
        TaskType.COVER_LETTER: "openai",  # OpenAI for cover letters
        TaskType.EMAIL_DRAFTING: "grok",  # Grok for emails
        TaskType.FAST_SUMMARY: "groq",  # Groq for fast summaries
        TaskType.JOB_MATCHING: "gemini",  # Gemini for matching
    }

    def __init__(self):
        """Initialize router with all available providers."""
        self.providers: Dict[str, AIProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize all configured AI providers."""
        # OpenAI
        if settings.OPENAI_API_KEY:
            try:
                self.providers["openai"] = OpenAIProvider(
                    api_key=settings.OPENAI_API_KEY,
                    model_name="gpt-4-turbo-preview"
                )
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        # Grok
        if settings.GROK_API_KEY:
            try:
                self.providers["grok"] = GrokProvider(
                    api_key=settings.GROK_API_KEY,
                    model_name="grok-beta"
                )
                logger.info("Grok provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Grok: {e}")

        # Gemini
        if settings.GEMINI_API_KEY:
            try:
                self.providers["gemini"] = GeminiProvider(
                    api_key=settings.GEMINI_API_KEY,
                    model_name="gemini-pro"
                )
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        # Groq
        if settings.GROQ_API_KEY:
            try:
                self.providers["groq"] = GroqProvider(
                    api_key=settings.GROQ_API_KEY,
                    model_name="llama-2-70b-4096"
                )
                logger.info("Groq provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")

    def get_provider(
        self,
        task_type: TaskType,
        preferred_provider: Optional[str] = None,
        fallback: bool = True
    ) -> Optional[AIProvider]:
        """
        Get appropriate provider for a task.
        
        Args:
            task_type: Type of task
            preferred_provider: User's preferred provider (if any)
            fallback: Whether to use fallback if preferred unavailable
            
        Returns:
            AIProvider: Provider instance, or None if none available
        """
        # Try preferred provider first
        if preferred_provider and preferred_provider in self.providers:
            provider = self.providers[preferred_provider]
            if self._is_provider_suitable(provider, task_type):
                return provider

        # Use default for task type
        default_provider_name = self.DEFAULT_MODELS.get(task_type)
        if default_provider_name and default_provider_name in self.providers:
            provider = self.providers[default_provider_name]
            if self._is_provider_suitable(provider, task_type):
                return provider

        # Fallback to any available provider
        if fallback:
            for provider_name, provider in self.providers.items():
                if self._is_provider_suitable(provider, task_type):
                    logger.info(f"Using fallback provider: {provider_name}")
                    return provider

        logger.error(f"No available provider for task: {task_type}")
        return None

    def _is_provider_suitable(self, provider: AIProvider, task_type: TaskType) -> bool:
        """
        Check if provider is suitable for task type.
        
        Args:
            provider: Provider instance
            task_type: Task type
            
        Returns:
            bool: True if suitable
        """
        # All providers are suitable for all tasks currently
        # Can add task-specific logic here if needed
        return True

    async def generate(
        self,
        task_type: TaskType,
        prompt: str,
        system_prompt: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using appropriate provider.
        
        Args:
            task_type: Type of task
            prompt: User prompt
            system_prompt: Optional system prompt
            preferred_provider: Preferred provider name
            **kwargs: Additional parameters
            
        Returns:
            str: Generated text, or None if generation failed
        """
        provider = self.get_provider(task_type, preferred_provider)
        if not provider:
            logger.error(f"No provider available for task: {task_type}")
            return None

        try:
            result = await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                **kwargs
            )
            logger.info(f"Generated text using {provider.__class__.__name__}")
            return result
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            # Try fallback if not already using it
            if preferred_provider:
                fallback_provider = self.get_provider(
                    task_type, preferred_provider=None, fallback=True
                )
                if fallback_provider and fallback_provider != provider:
                    try:
                        return await fallback_provider.generate(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            **kwargs
                        )
                    except Exception as fallback_error:
                        logger.error(f"Fallback generation failed: {fallback_error}")
            return None


# Global router instance
model_router = ModelRouter()

