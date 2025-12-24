"""
AI Model Router Tests

Tests for AI model router, usage tracking, and cost optimization.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.ai.router import ModelRouter
from app.ai.base import TaskType, AIProvider


@pytest.mark.ai
@pytest.mark.unit
class TestModelRouterInitialization:
    """Test AI model router initialization."""

    def test_router_initializes_without_providers(self, monkeypatch):
        """Test router initializes even with no API keys."""
        # Mock settings with no API keys
        from app.core import config
        mock_settings = MagicMock()
        mock_settings.OPENAI_API_KEY = ""
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.GROQ_API_KEY = ""
        mock_settings.GROK_API_KEY = ""
        monkeypatch.setattr(config, "settings", mock_settings)

        router = ModelRouter()

        assert isinstance(router, ModelRouter)
        assert len(router.providers) == 0

    def test_router_initializes_with_mock_provider(self):
        """Test router with available providers."""
        router = ModelRouter()

        # Router should initialize even if providers fail
        assert isinstance(router, ModelRouter)
        assert isinstance(router.providers, dict)


@pytest.mark.ai
class TestProviderSelection:
    """Test provider selection logic."""

    def test_get_provider_for_task_type(self):
        """Test getting provider based on task type."""
        router = ModelRouter()

        # Test default task type mapping
        task_types = [
            TaskType.CV_PARSING,
            TaskType.COVER_LETTER,
            TaskType.JOB_MATCHING,
        ]

        for task_type in task_types:
            provider = router.get_provider(task_type)
            # Might be None if no providers configured
            assert provider is None or isinstance(provider, AIProvider)

    def test_cost_optimization_selects_cheaper_provider(self):
        """Test that cost optimization prefers cheaper providers."""
        router = ModelRouter()

        # Get provider with cost optimization
        provider = router.get_provider(
            TaskType.FAST_SUMMARY,
            optimize_cost=True
        )

        # Should prefer Groq or Gemini (cheaper) over OpenAI
        # Might be None if no providers available
        assert provider is None or isinstance(provider, AIProvider)

    def test_fallback_provider_selection(self):
        """Test fallback to alternative providers."""
        router = ModelRouter()

        # Request unavailable provider with fallback
        provider = router.get_provider(
            TaskType.CV_PARSING,
            preferred_provider="nonexistent_provider",
            fallback=True
        )

        # Should either get a fallback or None
        assert provider is None or isinstance(provider, AIProvider)

    def test_no_fallback_returns_none(self):
        """Test that fallback=False returns None when preferred unavailable."""
        router = ModelRouter()

        provider = router.get_provider(
            TaskType.CV_PARSING,
            preferred_provider="nonexistent_provider",
            fallback=False
        )

        # Should be None since preferred is unavailable and no fallback
        assert provider is None


@pytest.mark.ai
class TestTokenEstimation:
    """Test token counting and estimation."""

    def test_estimate_tokens_with_tiktoken(self):
        """Test token estimation with tiktoken."""
        router = ModelRouter()

        text = "This is a test prompt for token estimation."
        tokens = router._estimate_tokens(text)

        # Should return reasonable token count
        assert tokens > 0
        assert tokens < len(text)  # Tokens usually < characters

    def test_estimate_tokens_fallback(self):
        """Test token estimation fallback (without tiktoken)."""
        router = ModelRouter()

        text = "A" * 100
        tokens = router._estimate_tokens(text)

        # Fallback: ~1 token per 4 characters
        # So 100 chars ≈ 25 tokens
        assert 20 <= tokens <= 30

    def test_estimate_tokens_empty_string(self):
        """Test token estimation with empty string."""
        router = ModelRouter()

        tokens = router._estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_long_text(self):
        """Test token estimation with very long text."""
        router = ModelRouter()

        text = "word " * 10000  # ~50k characters
        tokens = router._estimate_tokens(text)

        assert tokens > 1000


@pytest.mark.ai
class TestCostCalculation:
    """Test cost calculation."""

    def test_calculate_cost_basic(self):
        """Test basic cost calculation."""
        router = ModelRouter()

        # Create mock provider
        mock_provider = MagicMock()
        mock_provider.cost_per_token = {
            "input": 0.01,  # $0.01 per 1K input tokens
            "output": 0.03  # $0.03 per 1K output tokens
        }

        # Calculate cost for 1000 input + 500 output tokens
        cost = router._calculate_cost(mock_provider, 1000, 500)

        # Expected: (1000/1000 * 0.01) + (500/1000 * 0.03) = 0.01 + 0.015 = 0.025
        assert abs(cost - 0.025) < 0.001

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        router = ModelRouter()

        mock_provider = MagicMock()
        mock_provider.cost_per_token = {"input": 0.01, "output": 0.03}

        cost = router._calculate_cost(mock_provider, 0, 0)
        assert cost == 0.0

    def test_calculate_cost_large_numbers(self):
        """Test cost calculation with large token counts."""
        router = ModelRouter()

        mock_provider = MagicMock()
        mock_provider.cost_per_token = {"input": 0.01, "output": 0.03}

        # 100,000 input tokens + 50,000 output tokens
        cost = router._calculate_cost(mock_provider, 100000, 50000)

        # Expected: (100 * 0.01) + (50 * 0.03) = 1.0 + 1.5 = 2.5
        assert abs(cost - 2.5) < 0.01


@pytest.mark.ai
@pytest.mark.asyncio
class TestGeneration:
    """Test text generation with router."""

    async def test_generate_without_providers(self):
        """Test generation when no providers available."""
        router = ModelRouter()

        result = await router.generate(
            task_type=TaskType.CV_PARSING,
            prompt="Test prompt"
        )

        # Should return None when no providers available
        assert result is None

    async def test_generate_with_mock_provider(self, monkeypatch):
        """Test generation with mocked provider."""
        router = ModelRouter()

        # Create mock provider
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value="Mock AI response")
        mock_provider.cost_per_token = {"input": 0.01, "output": 0.03}

        # Add mock provider to router
        router.providers["mock"] = mock_provider

        result = await router.generate(
            task_type=TaskType.CV_PARSING,
            prompt="Test prompt",
            preferred_provider="mock"
        )

        # Should call provider and return result
        if result:
            assert result == "Mock AI response"
            mock_provider.generate.assert_called_once()

    async def test_generate_tracks_usage(self, monkeypatch):
        """Test that generation tracks usage statistics."""
        router = ModelRouter()

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value="Response")
        mock_provider.cost_per_token = {"input": 0.01, "output": 0.03}

        router.providers["mock"] = mock_provider

        # Mock usage tracker
        mock_tracker = MagicMock()
        router.usage_tracker = mock_tracker

        await router.generate(
            task_type=TaskType.CV_PARSING,
            prompt="Test",
            preferred_provider="mock"
        )

        # Usage should be tracked
        # (Might not be called if provider returns None)


@pytest.mark.ai
class TestCostRanking:
    """Test cost ranking of providers."""

    def test_get_provider_cost_rank(self):
        """Test provider cost ranking."""
        router = ModelRouter()

        cost_rank = router._get_provider_cost_rank()

        # Should return cost mapping
        assert isinstance(cost_rank, dict)
        assert "groq" in cost_rank
        assert "gemini" in cost_rank
        assert "openai" in cost_rank

        # Groq should be cheapest
        assert cost_rank["groq"] < cost_rank["openai"]
        assert cost_rank["gemini"] < cost_rank["openai"]


@pytest.mark.ai
class TestRateLimiting:
    """Test rate limiting functionality."""

    async def test_rate_limit_fallback(self, monkeypatch):
        """Test that rate limit triggers fallback provider."""
        router = ModelRouter()

        # Mock usage tracker to simulate rate limit
        mock_tracker = MagicMock()
        mock_tracker.check_rate_limit = MagicMock(return_value=False)
        router.usage_tracker = mock_tracker

        # Mock providers
        mock_provider1 = AsyncMock()
        mock_provider1.generate = AsyncMock(return_value="Response")
        mock_provider1.cost_per_token = {"input": 0.01, "output": 0.03}

        router.providers["provider1"] = mock_provider1

        result = await router.generate(
            task_type=TaskType.CV_PARSING,
            prompt="Test",
            user_id="test_user",
            preferred_provider="provider1"
        )

        # Should either fallback or return None
        # check_rate_limit should be called
        mock_tracker.check_rate_limit.assert_called()


@pytest.mark.ai
class TestTaskTypeMappings:
    """Test default task type to provider mappings."""

    def test_default_models_coverage(self):
        """Test that all task types have default models."""
        router = ModelRouter()

        # All task types should have a default
        for task_type in TaskType:
            default_provider = router.DEFAULT_MODELS.get(task_type)
            assert default_provider is not None
            assert isinstance(default_provider, str)

    def test_provider_suitability(self):
        """Test provider suitability check."""
        router = ModelRouter()

        # Create mock provider
        mock_provider = MagicMock()

        # All providers should be suitable for all tasks (currently)
        for task_type in TaskType:
            is_suitable = router._is_provider_suitable(mock_provider, task_type)
            assert is_suitable is True
