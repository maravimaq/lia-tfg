from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    google_web_client_id: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()