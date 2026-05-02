from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    google_web_client_id: str | None = None
    scraping_sources_json: str | None = None
    scraping_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    scraping_timeout_seconds: int = 25

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()