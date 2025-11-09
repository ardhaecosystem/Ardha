"""
Configuration settings for Ardha backend application.

Uses Pydantic BaseSettings to load and validate environment variables.
All settings are properly typed and validated at startup.
"""

from functools import lru_cache
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    """Database configuration settings."""
    
    url: str = Field(
        default="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev",
        description="Database connection URL"
    )
    pool_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Database connection pool size"
    )
    max_overflow: int = Field(
        default=0,
        ge=0,
        le=50,
        description="Maximum overflow connections beyond pool size"
    )
    
    @property
    def sqlalchemy_database_uri(self) -> str:
        """Get the SQLAlchemy database URI."""
        return self.url


class RedisSettings(BaseModel):
    """Redis configuration settings."""
    
    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    max_connections: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum Redis connections"
    )


class QdrantSettings(BaseModel):
    """Qdrant vector database configuration settings."""
    
    url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL"
    )
    collection_prefix: str = Field(
        default="ardha_dev",
        description="Prefix for Qdrant collection names"
    )


class SecuritySettings(BaseModel):
    """Security configuration settings."""
    
    jwt_secret_key: str = Field(
        description="JWT secret key for token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT algorithm for token signing"
    )
    jwt_access_token_expire_minutes: int = Field(
        default=15,
        ge=1,
        le=1440,
        description="JWT access token expiration in minutes"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="JWT refresh token expiration in days"
    )
    session_secret_key: Optional[str] = Field(
        default=None,
        description="Session secret key for session management"
    )
    session_cookie_secure: bool = Field(
        default=False,
        description="Whether session cookies should be secure (HTTPS only)"
    )
    session_cookie_httponly: bool = Field(
        default=True,
        description="Whether session cookies should be HTTP only"
    )
    
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate JWT secret key is not too short."""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v


class AISettings(BaseModel):
    """AI service configuration settings."""
    
    openrouter_api_key: str = Field(
        description="OpenRouter API key for AI services"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    openrouter_timeout: int = Field(
        default=300,
        ge=1,
        le=600,
        description="OpenRouter request timeout in seconds"
    )
    openrouter_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for OpenRouter requests"
    )
    openrouter_circuit_breaker_threshold: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of failures before circuit breaker opens"
    )
    openrouter_circuit_breaker_cooldown: int = Field(
        default=300,
        ge=60,
        le=1800,
        description="Circuit breaker cooldown period in seconds"
    )


class EmailSettings(BaseModel):
    """Email configuration settings."""
    
    host: Optional[str] = Field(
        default=None,
        description="SMTP server host"
    )
    port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP server port"
    )
    user: Optional[str] = Field(
        default=None,
        description="SMTP username"
    )
    password: Optional[str] = Field(
        default=None,
        description="SMTP password"
    )
    tls: bool = Field(
        default=True,
        description="Whether to use TLS for SMTP"
    )


class OAuthSettings(BaseModel):
    """OAuth configuration settings."""
    
    github_client_id: Optional[str] = Field(
        default=None,
        description="GitHub OAuth client ID"
    )
    github_client_secret: Optional[str] = Field(
        default=None,
        description="GitHub OAuth client secret"
    )
    google_client_id: Optional[str] = Field(
        default=None,
        description="Google OAuth client ID"
    )
    google_client_secret: Optional[str] = Field(
        default=None,
        description="Google OAuth client secret"
    )


class FileSettings(BaseModel):
    """File storage configuration settings."""
    
    upload_dir: str = Field(
        default="./uploads",
        description="Directory for file uploads"
    )
    max_file_size: int = Field(
        default=10485760,  # 10MB
        ge=1024,  # 1KB minimum
        description="Maximum file size in bytes"
    )


class RateLimitSettings(BaseModel):
    """Rate limiting configuration settings."""
    
    per_minute: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Rate limit requests per minute"
    )
    burst: int = Field(
        default=200,
        ge=1,
        le=20000,
        description="Rate limit burst size"
    )


class CORSSettings(BaseModel):
    """CORS configuration settings."""
    
    origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    allow_credentials: bool = Field(
        default=True,
        description="Whether to allow credentials in CORS requests"
    )
    
    @field_validator("origins", mode="before")
    @classmethod
    def parse_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class Settings(BaseSettings):
    """Main application settings."""
    
    app_env: str = Field(
        default="development",
        pattern="^(development|testing|staging|production)$",
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level"
    )
    
    # Sub-settings (use BaseModel for nested, not BaseSettings)
    # Environment variables with nested delimiter (__) will populate these
    database: DatabaseSettings = Field(default_factory=lambda: DatabaseSettings())
    redis: RedisSettings = Field(default_factory=lambda: RedisSettings())
    qdrant: QdrantSettings = Field(default_factory=lambda: QdrantSettings())
    security: SecuritySettings = Field(default_factory=lambda: SecuritySettings(jwt_secret_key=""))
    ai: AISettings = Field(default_factory=lambda: AISettings(openrouter_api_key=""))
    email: EmailSettings = Field(default_factory=lambda: EmailSettings())
    oauth: OAuthSettings = Field(default_factory=lambda: OAuthSettings())
    files: FileSettings = Field(default_factory=lambda: FileSettings())
    rate_limit: RateLimitSettings = Field(default_factory=lambda: RateLimitSettings())
    cors: CORSSettings = Field(default_factory=lambda: CORSSettings())
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.app_env == "testing"
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        return self.cors.origins
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()