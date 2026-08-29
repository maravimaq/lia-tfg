from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Entorno de ejecución
    environment: str = "development"

    # Base de datos y seguridad
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # En desarrollo podemos crear las tablas automáticamente.
    # En producción se desactivará y utilizaremos Alembic.
    create_tables_on_startup: bool = True

    # Orígenes separados por comas.
    cors_origins: str = (
        "http://localhost:8081,"
        "http://127.0.0.1:8081,"
        "http://localhost:19006,"
        "http://127.0.0.1:19006"
    )

    google_web_client_id: str | None = None

    # Scraping
    scraping_sources_json: str | None = None
    scraping_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    scraping_timeout_seconds: int = 25

    # Correo
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "LIA"
    smtp_use_tls: bool = True
    password_reset_url: str = "lia://reset-password"

    # IA
    # Valores admitidos: cloudflare, ollama o mock.
    ai_provider: str = "cloudflare"

    # Cloudflare Workers AI
    cloudflare_account_id: str | None = None
    cloudflare_ai_token: str | None = None
    cloudflare_ai_model: str = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    cloudflare_ai_timeout_seconds: int = 90

    # Ollama (opcional para desarrollo local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: int = 300

    # Telegram
    telegram_bot_token: str | None = None
    telegram_webhook_base_url: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_request_timeout_seconds: int = 10

    # DIA
    dia_cookie: str | None = None
    dia_max_categories: int = 20
    dia_max_pages_per_category: int = 3

    # Mercadona
    mercadona_max_categories: int = 40

    # Carrefour
    carrefour_max_urls: int = 8
    carrefour_max_products_per_url: int = 40
    carrefour_max_pages_per_url: int = 5
    carrefour_use_playwright_fallback: bool = True

    # ALDI
    aldi_max_listing_urls: int = 1
    aldi_max_article_links: int = 120
    aldi_max_products: int = 250
    aldi_use_playwright_fallback: bool = True

    # Alcampo
    alcampo_max_urls: int = 3
    alcampo_max_products_per_url: int = 80
    alcampo_use_playwright_fallback: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte CORS_ORIGINS en una lista limpia de orígenes."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()