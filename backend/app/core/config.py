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

    # DIA
    dia_cookie: str | None = None
    dia_max_categories: int = 20
    dia_max_pages_per_category: int = 3
    
    # Mercadona
    mercadona_max_categories: int = 40
    
    # Carrefour
    carrefour_max_urls: int = 3
    carrefour_max_products_per_url: int = 40
    carrefour_use_playwright_fallback: bool = True
    
    # ALDI
    aldi_max_listing_urls: int = 3
    aldi_max_article_links: int = 120
    aldi_max_products: int = 120
    aldi_use_playwright_fallback: bool = True
    
    # Alcampo
    alcampo_max_urls: int = 3
    alcampo_max_products_per_url: int = 80
    alcampo_use_playwright_fallback: bool = True

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()