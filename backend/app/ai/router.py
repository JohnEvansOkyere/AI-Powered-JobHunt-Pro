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
from app.ai.usage_tracker import get_usage_tracker
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Optional tiktoken import for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not installed. Using fallback token estimation. Install with: pip install tiktoken")
# Import providers with error handling for missing dependencies
try:
    from app.ai.providers.openai_provider import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from app.ai.providers.grok_provider import GrokProvider
except ImportError:
    GrokProvider = None

try:
    from app.ai.providers.gemini_provider import GeminiProvider
except ImportError:
    GeminiProvider = None

try:
    from app.ai.providers.groq_provider import GroqProvider
except ImportError:
    GroqProvider = None


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
        TaskType.CV_PARSING: "openai",  # OpenAI for CV parsing (structured extraction)
    }

    def __init__(self):
        """Initialize router with all available providers."""
        self.providers: Dict[str, AIProvider] = {}
        self.usage_tracker = get_usage_tracker()
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize all configured AI providers."""
        # OpenAI
        if settings.OPENAI_API_KEY and OpenAIProvider is not None:
            try:
                self.providers["openai"] = OpenAIProvider(
                    api_key=settings.OPENAI_API_KEY,
                    model_name="gpt-4-turbo-preview"
                )
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        # Grok
        if settings.GROK_API_KEY and GrokProvider is not None:
            try:
                self.providers["grok"] = GrokProvider(
                    api_key=settings.GROK_API_KEY,
                    model_name="grok-beta"
                )
                logger.info("Grok provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Grok: {e}")

        # Gemini
        if settings.GEMINI_API_KEY and GeminiProvider is not None:
            try:
                self.providers["gemini"] = GeminiProvider(
                    api_key=settings.GEMINI_API_KEY,
                    model_name="gemini-pro"
                )
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        # Groq
        if settings.GROQ_API_KEY and GroqProvider is not None:
            try:
                self.providers["groq"] = GroqProvider(
                    api_key=settings.GROQ_API_KEY,
                    model_name="llama-2-70b-4096"
                )
                logger.info("Groq provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")

    def _get_provider_cost_rank(self) -> Dict[str, float]:
        """
        Get providers ranked by cost (cheapest first).
        
        Returns:
            dict: Provider name -> average cost per 1K tokens
        """
        # Cost per 1K tokens (input + output average)
        costs = {
            "groq": 0.0007,  # Very cheap
            "gemini": 0.001,  # Cheap
            "grok": 0.01,  # Moderate
            "openai": 0.02,  # Expensive (GPT-4 Turbo)
        }
        return costs
    
    def get_provider(
        self,
        task_type: TaskType,
        preferred_provider: Optional[str] = None,
        fallback: bool = True,
        optimize_cost: bool = False
    ) -> Optional[AIProvider]:
        """
        Get appropriate provider for a task.
        
        Args:
            task_type: Type of task
            preferred_provider: User's preferred provider (if any)
            fallback: Whether to use fallback if preferred unavailable
            optimize_cost: If True, prefer cheaper providers
            
        Returns:
            AIProvider: Provider instance, or None if none available
        """
        # Try preferred provider first (unless cost optimization is enabled)
        if preferred_provider and preferred_provider in self.providers and not optimize_cost:
            provider = self.providers[preferred_provider]
            if self._is_provider_suitable(provider, task_type):
                return provider

        # Use default for task type (unless cost optimization)
        if not optimize_cost:
            default_provider_name = self.DEFAULT_MODELS.get(task_type)
            if default_provider_name and default_provider_name in self.providers:
                provider = self.providers[default_provider_name]
                if self._is_provider_suitable(provider, task_type):
                    return provider

        # Cost optimization: prefer cheaper providers
        if optimize_cost:
            cost_rank = self._get_provider_cost_rank()
            sorted_providers = sorted(
                cost_rank.items(),
                key=lambda x: x[1]
            )
            for provider_name, _ in sorted_providers:
                if provider_name in self.providers:
                    provider = self.providers[provider_name]
                    if self._is_provider_suitable(provider, task_type):
                        logger.info(f"Using cost-optimized provider: {provider_name}")
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

    def _estimate_tokens(self, text: str, model: str = "gpt-4") -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to estimate
            model: Model name (for tokenizer selection)
            
        Returns:
            int: Estimated token count
        """
        if TIKTOKEN_AVAILABLE:
            try:
                # Use tiktoken for accurate token counting (OpenAI models)
                encoding = tiktoken.encoding_for_model(model)
                return len(encoding.encode(text))
            except Exception as e:
                logger.warning(f"tiktoken encoding failed, using fallback: {e}")
                # Fallback: rough estimate (1 token ≈ 4 characters)
                return len(text) // 4
        else:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
    
    def _calculate_cost(
        self,
        provider: AIProvider,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost for API call.
        
        Args:
            provider: Provider instance
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            
        Returns:
            float: Cost in USD
        """
        costs = provider.cost_per_token
        input_cost = (input_tokens / 1000) * costs.get("input", 0)
        output_cost = (output_tokens / 1000) * costs.get("output", 0)
        return input_cost + output_cost
    
    async def generate(
        self,
        task_type: TaskType,
        prompt: str,
        system_prompt: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        user_id: Optional[str] = None,
        optimize_cost: bool = False,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using appropriate provider with cost tracking.
        
        Args:
            task_type: Type of task
            prompt: User prompt
            system_prompt: Optional system prompt
            preferred_provider: Preferred provider name
            user_id: User ID for rate limiting (optional)
            optimize_cost: If True, prefer cheaper providers
            **kwargs: Additional parameters
            
        Returns:
            str: Generated text, or None if generation failed
        """
        provider = self.get_provider(task_type, preferred_provider, optimize_cost=optimize_cost)
        if not provider:
            logger.error(f"No provider available for task: {task_type}")
            return None

        # Check rate limit (if user_id provided)
        if user_id:
            provider_name = next(
                (name for name, p in self.providers.items() if p == provider),
                "unknown"
            )
            if not self.usage_tracker.check_rate_limit(user_id, provider_name):
                logger.warning(f"Rate limit exceeded for user {user_id}")
                # Try fallback provider
                fallback_provider = self.get_provider(
                    task_type, preferred_provider=None, fallback=True
                )
                if fallback_provider and fallback_provider != provider:
                    provider = fallback_provider
                    provider_name = next(
                        (name for name, p in self.providers.items() if p == fallback_provider),
                        "unknown"
                    )
                else:
                    return None

        # Estimate input tokens
        full_prompt = (system_prompt or "") + prompt
        input_tokens = self._estimate_tokens(full_prompt)

        try:
            result = await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                **kwargs
            )
            
            if result:
                # Estimate output tokens
                output_tokens = self._estimate_tokens(result)
                
                # Calculate cost
                cost = self._calculate_cost(provider, input_tokens, output_tokens)
                
                # Track usage
                provider_name = next(
                    (name for name, p in self.providers.items() if p == provider),
                    "unknown"
                )
                self.usage_tracker.record_usage(
                    task_type=task_type.value,
                    provider=provider_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    success=True
                )
                
                logger.info(
                    f"Generated text using {provider.__class__.__name__} "
                    f"({input_tokens} in, {output_tokens} out, ${cost:.4f})"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            
            # Track failed usage
            provider_name = next(
                (name for name, p in self.providers.items() if p == provider),
                "unknown"
            )
            self.usage_tracker.record_usage(
                task_type=task_type.value,
                provider=provider_name,
                input_tokens=input_tokens,
                output_tokens=0,
                cost=0.0,
                success=False,
                error=str(e)
            )
            
            # Try fallback if not already using it
            if preferred_provider:
                fallback_provider = self.get_provider(
                    task_type, preferred_provider=None, fallback=True
                )
                if fallback_provider and fallback_provider != provider:
                    try:
                        # Recursive call but with preferred_provider=None to avoid infinite loop
                        fallback_input_tokens = self._estimate_tokens((system_prompt or "") + prompt)
                        fallback_result = await fallback_provider.generate(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            **kwargs
                        )
                        
                        if fallback_result:
                            fallback_output_tokens = self._estimate_tokens(fallback_result)
                            fallback_cost = self._calculate_cost(fallback_provider, fallback_input_tokens, fallback_output_tokens)
                            fallback_provider_name = next(
                                (name for name, p in self.providers.items() if p == fallback_provider),
                                "unknown"
                            )
                            self.usage_tracker.record_usage(
                                task_type=task_type.value,
                                provider=fallback_provider_name,
                                input_tokens=fallback_input_tokens,
                                output_tokens=fallback_output_tokens,
                                cost=fallback_cost,
                                success=True
                            )
                            logger.info(f"Fallback generation succeeded using {fallback_provider.__class__.__name__}")
                            return fallback_result
                    except Exception as fallback_error:
                        logger.error(f"Fallback generation failed: {fallback_error}")
            return None


# Global router instance (lazy initialization)
_model_router: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    """Get or create the global model router instance."""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router

# For backward compatibility
model_router = get_model_router()

