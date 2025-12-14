"""
Application Configuration

Centralized configuration management using Pydantic Settings.
All environment variables are loaded here with validation and defaults.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
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

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"], description="Allowed hosts for TrustedHost middleware"
    )

    # Sentry
    SENTRY_DSN: str = Field(default="", description="Sentry DSN for error tracking")

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

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"


# Global settings instance
settings = Settings()

