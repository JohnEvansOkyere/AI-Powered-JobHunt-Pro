"""
Application Configuration

Centralized configuration management using Pydantic Settings.
All environment variables are loaded here with validation and defaults.
"""

from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_parse_none_str="null",
    )

    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=True, description="Debug mode")
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration in minutes"
    )

    # Supabase Configuration
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_KEY: str = Field(..., description="Supabase anon/public key")
    SUPABASE_SERVICE_KEY: str = Field(..., description="Supabase service role key")
    SUPABASE_JWT_SECRET: str = Field(
        default="",
        description="Supabase JWT secret for local access-token verification",
    )
    SUPABASE_STORAGE_BUCKET: str = Field(
        default="cvs", description="Supabase storage bucket name for CVs"
    )

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL database connection URL")
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate DATABASE_URL format."""
        if not v or v.strip() == "":
            raise ValueError("DATABASE_URL cannot be empty")
        
        # Basic validation - should start with postgresql://
        if not v.startswith("postgresql://") and not v.startswith("postgresql+psycopg2://"):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql://' or 'postgresql+psycopg2://'. "
                f"Got: {v[:20]}..."
            )
        
        return v

    # AI Provider API Keys
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    GROK_API_KEY: str = Field(default="", description="Grok API key")
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GROQ_API_KEY: str = Field(default="", description="Groq API key")

    # Job Scraper API Keys (all optional - some FREE scrapers work without any keys)
    SERPAPI_API_KEY: str = Field(default="", description="SerpAPI key for Google Jobs (PAID)")
    JOOBLE_API_KEY: str = Field(default="", description="Jooble API key (FREE from jooble.org/api/about)")
    FINDWORK_API_KEY: str = Field(default="", description="FindWork.dev API key (FREE tier: 50 req/day)")
    ADZUNA_APP_ID: str = Field(default="", description="Adzuna App ID (FREE from developer.adzuna.com)")
    ADZUNA_APP_KEY: str = Field(default="", description="Adzuna App Key (FREE from developer.adzuna.com)")

    # Celery & Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0", description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0", description="Celery result backend URL"
    )

    # Scheduler
    # After the Phase 2 migration (see docs/RECOMMENDATIONS_V2_PLAN.md §7),
    # Celery Beat owns all periodic jobs. Set to "disabled" to bypass the
    # in-process startup hook entirely (useful if ops need to stop periodic
    # work without redeploying).
    SCHEDULER_MODE: str = Field(
        default="celery",
        description="Scheduler mode: 'celery' (Celery Beat) or 'disabled'.",
    )

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )
    ALLOWED_HOSTS: Union[str, List[str]] = Field(
        default=["*"], description="Allowed hosts for TrustedHost middleware"
    )

    # Sentry
    SENTRY_DSN: str = Field(default="", description="Sentry DSN for error tracking")

    # Cron / scheduled task auth (optional - for triggering cleanup from external cron)
    CRON_SECRET: str = Field(
        default="",
        description="Secret for cron endpoints (X-Cron-Secret header). If set, required to trigger cleanup.",
    )

    # Job Scraping
    SCRAPING_USER_AGENT: str = Field(
        default="Mozilla/5.0 (compatible; JobHuntBot/1.0)",
        description="User agent for web scraping",
    )
    SCRAPING_DELAY_SECONDS: float = Field(
        default=2.0, description="Delay between scraping requests (seconds)"
    )

    # Rate Limiting
    AI_RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, description="AI API rate limit per minute"
    )
    SCRAPING_RATE_LIMIT_PER_MINUTE: int = Field(
        default=10, description="Scraping rate limit per minute"
    )

    # ---- Recommendations V2 AI routing (docs/RECOMMENDATIONS_V2_PLAN.md §3.1) ----
    # Default to Gemini for both embedding and reranking (free-tier friendly).
    # Flip to OpenAI only if you explicitly want to pay for latency/capacity.
    AI_EMBEDDING_PROVIDER: str = Field(
        default="gemini",
        description="Provider for embeddings: 'gemini' (default, free), 'openai'.",
    )
    AI_EMBEDDING_MODEL: str = Field(
        default="gemini-embedding-001",
        description="Embedding model name. Must match job_embeddings.model at match time.",
    )
    AI_RERANK_PROVIDER: str = Field(
        default="gemini",
        description="Provider for top-K LLM reranker: 'gemini' (default, free), 'groq', 'openai'.",
    )
    AI_RERANK_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Rerank model name.",
    )
    AI_PROVIDER_FALLBACK_ENABLED: bool = Field(
        default=True,
        description="If True, a primary failure/timeout will fall back once to the paid provider.",
    )
    AI_EMBEDDING_TIMEOUT_SECONDS: float = Field(
        default=5.0,
        description="Hard timeout for a single embedding request before fallback kicks in.",
    )
    AI_RERANK_TIMEOUT_SECONDS: float = Field(
        default=45.0,
        description="Hard timeout for a single rerank request before fallback kicks in.",
    )

    # ---- WhatsApp Business Cloud API (docs/RECOMMENDATIONS_V2_PLAN.md §6) ----
    # All sends are gated by WHATSAPP_ENABLED so unconfigured environments
    # (CI, local dev without Meta access) no-op instead of 500ing. When
    # WHATSAPP_SEND_MODE is "dry_run" the client logs the payload and skips
    # the network call — useful for e2e tests and staging without a verified
    # sender.
    WHATSAPP_ENABLED: bool = Field(
        default=False,
        description="Master switch. Set to True only when credentials are valid + templates approved.",
    )
    WHATSAPP_SEND_MODE: str = Field(
        default="dry_run",
        description="Send mode: 'live' (call Meta), 'dry_run' (log + skip), 'sandbox' (send to test numbers only).",
    )

    # Cloud API credentials (required when WHATSAPP_ENABLED=True).
    WHATSAPP_APP_ID: str = Field(default="", description="Meta App ID.")
    WHATSAPP_APP_SECRET: str = Field(
        default="",
        description="Meta App secret. Used for the X-Hub-Signature-256 webhook HMAC.",
    )
    WHATSAPP_PHONE_NUMBER_ID: str = Field(
        default="",
        description="Meta Cloud API phone number id (NOT the display phone number).",
    )
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = Field(
        default="",
        description="WABA id. Needed for template submission, not sending.",
    )
    WHATSAPP_ACCESS_TOKEN: str = Field(
        default="",
        description="System-user access token with whatsapp_business_messaging scope.",
    )
    WHATSAPP_VERIFY_TOKEN: str = Field(
        default="",
        description="Arbitrary shared secret used in Meta's webhook verification handshake.",
    )
    WHATSAPP_GRAPH_API_VERSION: str = Field(
        default="v20.0",
        description="Meta Graph API version; bump when Meta deprecates the current one.",
    )
    WHATSAPP_TEMPLATE_OTP: str = Field(
        default="otp_verification",
        description="Pre-approved Cloud API template name for phone verification (AUTH category).",
    )
    WHATSAPP_TEMPLATE_DIGEST: str = Field(
        default="daily_job_digest",
        description="Pre-approved template for Tier-1 digest (MARKETING category).",
    )
    WHATSAPP_TEMPLATE_UNSUBSCRIBE: str = Field(
        default="unsubscribe_confirmation",
        description="Optional confirmation template after STOP (UTILITY category).",
    )

    # Guardrails.
    WHATSAPP_MAX_SENDS_PER_DAY: int = Field(
        default=5000,
        description="Global circuit breaker. If exceeded, dispatcher pauses itself.",
    )
    WHATSAPP_MAX_SENDS_PER_USER_PER_DAY: int = Field(
        default=1,
        description="Per-user cap. Prevents digest re-run bugs from spamming a candidate.",
    )
    WHATSAPP_PROVIDER_RPS: int = Field(
        default=5,
        description="Client-side rate limit (requests/sec) against the Cloud API.",
    )
    WHATSAPP_OTP_TTL_SECONDS: int = Field(
        default=600,
        description="How long a verification OTP stays valid in Redis.",
    )
    WHATSAPP_OTP_MAX_PER_HOUR: int = Field(
        default=3,
        description="Max OTP sends per user per hour (abuse guard).",
    )
    WHATSAPP_OTP_MAX_PER_DAY: int = Field(
        default=10,
        description="Max OTP sends per user per day.",
    )
    WHATSAPP_DEBUG_LOG_OTP: bool = Field(
        default=False,
        description="If True, log OTP codes at WARNING (local dev only; never enable in production).",
    )

    @field_validator("WHATSAPP_SEND_MODE", mode="before")
    @classmethod
    def _validate_send_mode(cls, v) -> str:
        allowed = {"live", "dry_run", "sandbox"}
        if isinstance(v, str) and v.strip().lower() in allowed:
            return v.strip().lower()
        return "dry_run"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return ["http://localhost:3000"]

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v) -> List[str]:
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        if isinstance(v, list):
            return v
        return ["*"]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def is_openai_configured(self) -> bool:
        """Check if OpenAI API key is set (for AI matching/recommendations). App does not crash if missing."""
        key = getattr(self, "OPENAI_API_KEY", None) or ""
        return bool(key and isinstance(key, str) and key.strip() != "")


# Global settings instance
settings = Settings()
