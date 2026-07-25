import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scraping.base import ScrapedProduct, ScraperRunResult
from app.scraping.catalog_importer import CatalogImportResult
from app.scraping.scraping_runner import (
    ScrapingExecutionSummary,
    ScrapingRunner,
    SourceExecutionResult,
)
import app.scraping.scraping_runner as runner_module


def source(status="success", **kwargs):
    return SourceExecutionResult(
        supermercado=kwargs.pop("supermercado", "DIA"),
        scraper_status=status,
        **kwargs,
    )


def test_source_and_summary_to_dict():
    item = source(created_count=2, updated_count=1)
    assert item.imported_count == 3
    assert item.to_dict()["imported_count"] == 3

    summary = ScrapingExecutionSummary(
        status="success", sources=[item], created_count=2, updated_count=1
    )
    assert summary.imported_count == 3
    assert summary.to_dict()["sources"][0]["supermercado"] == "DIA"


def test_normalize_supermarkets():
    assert ScrapingRunner._normalize_supermarkets(None) == {
        "DIA", "MERCADONA", "CARREFOUR", "ALDI", "ALCAMPO"
    }
    assert ScrapingRunner._normalize_supermarkets(
        [" dia ", "", None, "Mercadona"]
    ) == {"DIA", "MERCADONA"}


@pytest.mark.parametrize(
    ("sources", "expected"),
    [
        ([], "empty"),
        ([source("success"), source("success", supermercado="DIA2")], "success"),
        ([source("success"), source("blocked", supermercado="DIA2")], "partial"),
        ([source("blocked"), source("blocked", supermercado="DIA2")], "blocked"),
        ([source("error")], "error"),
    ],
)
def test_build_summary_statuses(sources, expected):
    runner = ScrapingRunner(MagicMock())
    summary = runner._build_summary(sources)
    assert summary.status == expected
    if sources:
        assert "Productos creados" in summary.message
    else:
        assert "ninguna fuente" in summary.message


def test_build_summary_suma_campos():
    runner = ScrapingRunner(MagicMock())
    summary = runner._build_summary([
        source(
            detected_count=3,
            accepted_count=2,
            rejected_count=1,
            created_count=1,
            updated_count=1,
            unchanged_count=2,
            duplicated_count=1,
        ),
        source(
            supermercado="Mercadona",
            detected_count=4,
            accepted_count=4,
            created_count=2,
        ),
    ])
    assert summary.detected_count == 7
    assert summary.accepted_count == 6
    assert summary.created_count == 3
    assert summary.updated_count == 1


def test_import_scraper_result_error_no_importa():
    runner = ScrapingRunner(MagicMock())
    runner.importer = MagicMock()
    result = runner._import_scraper_result(
        ScraperRunResult.failed("DIA", "boom"), commit=True
    )
    assert result.scraper_status == "error"
    assert result.error == "boom"
    runner.importer.import_products.assert_not_called()


def test_import_scraper_result_success_merge():
    runner = ScrapingRunner(MagicMock())
    runner.importer = MagicMock()
    runner.importer.import_products.return_value = CatalogImportResult(
        supermercado="DIA",
        created_count=2,
        updated_count=1,
        rejected_count=1,
        duplicated_count=1,
    )
    scraped = ScraperRunResult(
        supermercado="DIA",
        status="partial",
        products=[],
        detected_count=5,
        accepted_count=4,
        rejected_count=1,
        message="parcial",
        metadata={"m": 1},
    )
    result = runner._import_scraper_result(scraped, commit=False)
    assert result.created_count == 2
    assert result.updated_count == 1
    assert result.rejected_count == 2
    assert result.import_metadata["imported_count"] == 3
    runner.importer.import_products.assert_called_once_with(
        [], supermercado="DIA", commit=False
    )


def test_run_solo_fuentes_seleccionadas(monkeypatch):
    runner = ScrapingRunner(MagicMock())
    dia = AsyncMock(return_value=source("success", supermercado="DIA", created_count=1))
    aldi = AsyncMock(return_value=source("success", supermercado="ALDI", updated_count=1))
    runner._run_dia = dia
    runner._run_aldi = aldi
    runner._run_mercadona = AsyncMock()
    runner._run_carrefour = AsyncMock()
    runner._run_alcampo = AsyncMock()

    result = asyncio.run(runner.run(supermarkets=["dia", "aldi"], commit=False))
    assert result.status == "success"
    assert result.imported_count == 2
    dia.assert_awaited_once_with(commit=False)
    aldi.assert_awaited_once_with(commit=False)
    runner._run_mercadona.assert_not_awaited()


class FakeScraper:
    result = ScraperRunResult.success("DIA", [])
    last_kwargs = None
    last_instance = None

    def __init__(self, **kwargs):
        type(self).last_kwargs = kwargs
        type(self).last_instance = self
        self.close = AsyncMock()

    async def scrape(self):
        return type(self).result


@pytest.mark.parametrize(
    ("method_name", "class_name", "store"),
    [
        ("_run_dia", "DiaScraper", "DIA"),
        ("_run_mercadona", "MercadonaScraper", "Mercadona"),
        ("_run_carrefour", "CarrefourScraper", "Carrefour"),
        ("_run_aldi", "AldiScraper", "ALDI"),
        ("_run_alcampo", "AlcampoScraper", "Alcampo"),
    ],
)
def test_run_individual_scrapers(monkeypatch, method_name, class_name, store):
    fake_class = type(f"Fake{class_name}", (FakeScraper,), {})
    fake_class.result = ScraperRunResult.success(store, [])
    monkeypatch.setattr(runner_module, class_name, fake_class)

    runner = ScrapingRunner(MagicMock())
    runner._import_scraper_result = MagicMock(
        return_value=source("empty", supermercado=store)
    )
    result = asyncio.run(getattr(runner, method_name)(commit=True))

    assert result.supermercado == store
    fake_class.last_instance.close.assert_awaited_once()
    runner._import_scraper_result.assert_called_once()


def test_run_scraper_cierra_aunque_falle(monkeypatch):
    class Broken(FakeScraper):
        async def scrape(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(runner_module, "DiaScraper", Broken)
    runner = ScrapingRunner(MagicMock())
    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(runner._run_dia(commit=True))
    Broken.last_instance.close.assert_awaited_once()
