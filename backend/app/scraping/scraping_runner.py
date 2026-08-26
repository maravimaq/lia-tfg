from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.scraping.alcampo_scraper import AlcampoScraper
from app.scraping.aldi_scraper import AldiScraper
from app.scraping.base import DEFAULT_USER_AGENT, ScraperRunResult
from app.scraping.carrefour_scraper import CarrefourScraper
from app.scraping.catalog_importer import CatalogImporter, CatalogImportResult
from app.scraping.dia_scraper import DiaScraper
from app.scraping.mercadona_scraper import MercadonaScraper

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SourceExecutionResult:
    supermercado: str
    scraper_status: str

    detected_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0

    created_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    duplicated_count: int = 0

    message: Optional[str] = None
    error: Optional[str] = None

    scraper_metadata: dict = field(default_factory=dict)
    import_metadata: dict = field(default_factory=dict)

    @property
    def imported_count(self) -> int:
        return self.created_count + self.updated_count

    def to_dict(self) -> dict:
        return {
            "supermercado": self.supermercado,
            "scraper_status": self.scraper_status,
            "detected_count": self.detected_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "duplicated_count": self.duplicated_count,
            "imported_count": self.imported_count,
            "message": self.message,
            "error": self.error,
            "scraper_metadata": self.scraper_metadata,
            "import_metadata": self.import_metadata,
        }


@dataclass(slots=True)
class ScrapingExecutionSummary:
    status: str
    sources: list[SourceExecutionResult] = field(default_factory=list)

    detected_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0

    created_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    duplicated_count: int = 0

    message: Optional[str] = None

    @property
    def imported_count(self) -> int:
        return self.created_count + self.updated_count

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "detected_count": self.detected_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "duplicated_count": self.duplicated_count,
            "imported_count": self.imported_count,
            "message": self.message,
            "sources": [source.to_dict() for source in self.sources],
        }


class ScrapingRunner:
    """
    Orquestador de scraping de catálogo.

    Este runner debe ser llamado desde AdminService.
    AdminService no debería saber cómo parsear DIA, Mercadona, Carrefour, ALDI, Alcampo, etc.
    """

    def __init__(
        self,
        db: Session,
        *,
        timeout_seconds: int = 20,
        user_agent: str = DEFAULT_USER_AGENT,
        dia_cookie: Optional[str] = None,
        dia_max_categories: int = 20,
        dia_max_pages_per_category: int = 3,
        mercadona_max_categories: int = 40,
        carrefour_max_urls: int = 8,
        carrefour_max_pages_per_url: int = 5,
        carrefour_max_products_per_url: int = 40,
        carrefour_use_playwright_fallback: bool = True,
        aldi_max_listing_urls: int = 3,
        aldi_max_article_links: int = 120,
        aldi_max_products: int = 120,
        aldi_use_playwright_fallback: bool = True,
        alcampo_max_urls: int = 3,
        alcampo_max_products_per_url: int = 80,
        alcampo_use_playwright_fallback: bool = True,
    ) -> None:
        self.db = db
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

        self.dia_cookie = dia_cookie
        self.dia_max_categories = dia_max_categories
        self.dia_max_pages_per_category = dia_max_pages_per_category

        self.mercadona_max_categories = mercadona_max_categories

        self.carrefour_max_urls = carrefour_max_urls
        self.carrefour_max_pages_per_url = carrefour_max_pages_per_url
        self.carrefour_max_products_per_url = carrefour_max_products_per_url
        self.carrefour_use_playwright_fallback = carrefour_use_playwright_fallback

        self.aldi_max_listing_urls = aldi_max_listing_urls
        self.aldi_max_article_links = aldi_max_article_links
        self.aldi_max_products = aldi_max_products
        self.aldi_use_playwright_fallback = aldi_use_playwright_fallback

        self.alcampo_max_urls = alcampo_max_urls
        self.alcampo_max_products_per_url = alcampo_max_products_per_url
        self.alcampo_use_playwright_fallback = alcampo_use_playwright_fallback

        self.importer = CatalogImporter(db)

    async def run(
        self,
        *,
        supermarkets: Optional[list[str]] = None,
        commit: bool = True,
    ) -> ScrapingExecutionSummary:
        selected = self._normalize_supermarkets(supermarkets)

        source_results: list[SourceExecutionResult] = []

        if "DIA" in selected:
            source_results.append(
                await self._run_dia(commit=commit)
            )

        if "MERCADONA" in selected:
            source_results.append(
                await self._run_mercadona(commit=commit)
            )

        if "CARREFOUR" in selected:
            source_results.append(
                await self._run_carrefour(commit=commit)
            )

        if "ALDI" in selected:
            source_results.append(
                await self._run_aldi(commit=commit)
            )

        if "ALCAMPO" in selected:
            source_results.append(
                await self._run_alcampo(commit=commit)
            )

        summary = self._build_summary(source_results)

        logger.info(
            "Scraping finalizado: status=%s detectados=%s aceptados=%s "
            "creados=%s actualizados=%s rechazados=%s",
            summary.status,
            summary.detected_count,
            summary.accepted_count,
            summary.created_count,
            summary.updated_count,
            summary.rejected_count,
        )

        return summary

    async def _run_dia(self, *, commit: bool) -> SourceExecutionResult:
        scraper = DiaScraper(
            timeout_seconds=self.timeout_seconds,
            user_agent=self.user_agent,
            cookie=self.dia_cookie,
            max_categories=self.dia_max_categories,
            max_pages_per_category=self.dia_max_pages_per_category,
        )

        try:
            scraper_result = await scraper.scrape()
        finally:
            await scraper.close()

        return self._import_scraper_result(
            scraper_result,
            commit=commit,
        )

    async def _run_mercadona(self, *, commit: bool) -> SourceExecutionResult:
        scraper = MercadonaScraper(
            timeout_seconds=self.timeout_seconds,
            user_agent=self.user_agent,
            max_categories=self.mercadona_max_categories,
        )

        try:
            scraper_result = await scraper.scrape()
        finally:
            await scraper.close()

        return self._import_scraper_result(
            scraper_result,
            commit=commit,
        )

    async def _run_carrefour(self, *, commit: bool) -> SourceExecutionResult:
        scraper = CarrefourScraper(
            timeout_seconds=self.timeout_seconds,
            user_agent=self.user_agent,
            max_urls=self.carrefour_max_urls,
            max_products_per_url=self.carrefour_max_products_per_url,
            max_pages_per_url=self.carrefour_max_pages_per_url,
            use_playwright_fallback=self.carrefour_use_playwright_fallback,
        )

        try:
            scraper_result = await scraper.scrape()
        finally:
            await scraper.close()

        return self._import_scraper_result(
            scraper_result,
            commit=commit,
        )

    async def _run_aldi(self, *, commit: bool) -> SourceExecutionResult:
        scraper = AldiScraper(
            timeout_seconds=self.timeout_seconds,
            user_agent=self.user_agent,
            max_listing_urls=self.aldi_max_listing_urls,
            max_article_links=self.aldi_max_article_links,
            max_products=self.aldi_max_products,
            use_playwright_fallback=self.aldi_use_playwright_fallback,
        )

        try:
            scraper_result = await scraper.scrape()
        finally:
            await scraper.close()

        return self._import_scraper_result(
            scraper_result,
            commit=commit,
        )

    async def _run_alcampo(self, *, commit: bool) -> SourceExecutionResult:
        scraper = AlcampoScraper(
            timeout_seconds=self.timeout_seconds,
            user_agent=self.user_agent,
            max_urls=self.alcampo_max_urls,
            max_products_per_url=self.alcampo_max_products_per_url,
            use_playwright_fallback=self.alcampo_use_playwright_fallback,
        )

        try:
            scraper_result = await scraper.scrape()
        finally:
            await scraper.close()

        return self._import_scraper_result(
            scraper_result,
            commit=commit,
        )

    def _import_scraper_result(
        self,
        scraper_result: ScraperRunResult,
        *,
        commit: bool,
    ) -> SourceExecutionResult:
        if scraper_result.status not in {"success", "partial", "empty"}:
            return SourceExecutionResult(
                supermercado=scraper_result.supermercado,
                scraper_status=scraper_result.status,
                detected_count=scraper_result.detected_count,
                accepted_count=scraper_result.accepted_count,
                rejected_count=scraper_result.rejected_count,
                message=scraper_result.message,
                error=scraper_result.error,
                scraper_metadata=scraper_result.metadata,
            )

        import_result = self.importer.import_products(
            scraper_result.products,
            supermercado=scraper_result.supermercado,
            commit=commit,
        )

        return self._merge_results(
            scraper_result=scraper_result,
            import_result=import_result,
        )

    def _merge_results(
        self,
        *,
        scraper_result: ScraperRunResult,
        import_result: CatalogImportResult,
    ) -> SourceExecutionResult:
        return SourceExecutionResult(
            supermercado=scraper_result.supermercado,
            scraper_status=scraper_result.status,
            detected_count=scraper_result.detected_count,
            accepted_count=scraper_result.accepted_count,
            rejected_count=scraper_result.rejected_count + import_result.rejected_count,
            created_count=import_result.created_count,
            updated_count=import_result.updated_count,
            unchanged_count=import_result.unchanged_count,
            duplicated_count=import_result.duplicated_count,
            message=scraper_result.message,
            error=scraper_result.error,
            scraper_metadata=scraper_result.metadata,
            import_metadata=import_result.to_dict(),
        )

    def _build_summary(
        self,
        sources: list[SourceExecutionResult],
    ) -> ScrapingExecutionSummary:
        if not sources:
            return ScrapingExecutionSummary(
                status="empty",
                message="No se ha ejecutado ninguna fuente de scraping.",
            )

        statuses = {source.scraper_status for source in sources}

        if all(status == "success" for status in statuses):
            status = "success"
        elif any(status in {"success", "partial", "empty"} for status in statuses):
            status = "partial"
        elif all(status == "blocked" for status in statuses):
            status = "blocked"
        else:
            status = "error"

        summary = ScrapingExecutionSummary(
            status=status,
            sources=sources,
            detected_count=sum(source.detected_count for source in sources),
            accepted_count=sum(source.accepted_count for source in sources),
            rejected_count=sum(source.rejected_count for source in sources),
            created_count=sum(source.created_count for source in sources),
            updated_count=sum(source.updated_count for source in sources),
            unchanged_count=sum(source.unchanged_count for source in sources),
            duplicated_count=sum(source.duplicated_count for source in sources),
        )

        summary.message = (
            f"Scraping terminado con estado {summary.status}. "
            f"Productos creados: {summary.created_count}. "
            f"Productos actualizados: {summary.updated_count}."
        )

        return summary

    @staticmethod
    def _normalize_supermarkets(supermarkets: Optional[list[str]]) -> set[str]:
        if not supermarkets:
            return {"DIA", "MERCADONA", "CARREFOUR", "ALDI", "ALCAMPO"}

        return {
            supermarket.strip().upper()
            for supermarket in supermarkets
            if supermarket and supermarket.strip()
        }