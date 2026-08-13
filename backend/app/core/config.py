"""Application configuration.

All configuration comes from the environment (12-factor). Secrets are never
hardcoded and never have production-safe defaults: a placeholder JWT secret in a
production environment is a startup error, not a silent fallback.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent

DEV_PLACEHOLDER_SECRETS = frozenset(
    {
        "dev-secret-change-later",
        "dev-refresh-secret-change-later",
        "replace-me-with-a-long-random-access-secret",
        "replace-me-with-a-different-long-random-refresh-secret",
        "change-me",
    }
)


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        # backend/.env wins over the repository-root .env when both exist.
        env_file=(str(REPO_ROOT / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime ---
    app_name: str = "TWS E-Commerce API"
    environment: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- Datastores ---
    database_url: str
    test_database_url: str | None = None
    redis_url: str

    # Per worker process. Keep (pool_size + max_overflow) * workers well below
    # the Postgres max_connections limit, or put PgBouncer in front.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800
    db_echo: bool = False

    # --- Authentication ---
    jwt_secret: str
    jwt_refresh_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # --- HTTP ---
    # Browser origins allowed to call the API. Defaults to none: a client origin
    # is deployment configuration and must be granted explicitly.
    # NoDecode: accept a plain comma-separated env value (see validator below)
    # instead of requiring JSON in .env.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # --- Rate limiting ---
    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 60

    # --- Seed data ---
    seed_tenant_name: str = "Zeen"
    seed_tenant_slug: str = "zeen"
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept either a JSON list or a comma-separated string."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def is_testing(self) -> bool:
        return self.environment.lower() in {"test", "testing"}

    @model_validator(mode="after")
    def _reject_placeholder_secrets_outside_development(self) -> Settings:
        if self.is_production:
            placeholders = [
                name
                for name, value in (
                    ("JWT_SECRET", self.jwt_secret),
                    ("JWT_REFRESH_SECRET", self.jwt_refresh_secret),
                )
                if value in DEV_PLACEHOLDER_SECRETS or len(value) < 32
            ]
            if placeholders:
                raise ValueError(
                    "Refusing to start in production with weak/placeholder secrets: "
                    + ", ".join(placeholders)
                )
        if self.jwt_secret == self.jwt_refresh_secret:
            raise ValueError("JWT_SECRET and JWT_REFRESH_SECRET must differ")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


#: Convenience alias. Prefer `get_settings()` in new code so tests can override
#: the cache; this exists because several modules already import `settings`.
settings = get_settings()
