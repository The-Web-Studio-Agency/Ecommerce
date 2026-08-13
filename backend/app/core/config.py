from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TWS E-Commerce API"
    environment: str = "development"

    database_url: str
    redis_url: str

    jwt_secret: str
    jwt_refresh_secret: str

    access_token_expire_minutes: int = 30

    seed_admin_email: str | None = None
    seed_admin_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()