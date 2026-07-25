import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.scraping.base import ScrapedProduct, ScraperBlockedError
from app.scraping.dia_scraper import DiaScraper
from app.scraping.mercadona_scraper import MercadonaScraper
import app.scraping.dia_scraper as dia_module
import app.scraping.mercadona_scraper as merc_module


def http_error(status, url='https://example.test'):
    request = httpx.Request('GET', url)
    response = httpx.Response(status, request=request, text='error body')
    return httpx.HTTPStatusError('bad', request=request, response=response)


def valid_dia_item(**updates):
    item = {
        'display_name':'Leche entera 1 L',
        'prices': {'price':'1,25', 'price_per_unit':'1,25', 'measure_unit':'L'},
        'brand':'DIA', 'object_id':'123', 'url':'/leche', 'image':'/img.jpg',
    }
    item.update(updates)
    return item


def valid_merc_item(**updates):
    item = {
        'id': 10,
        'display_name':'Leche entera',
        'price_instructions': {'unit_price':'1.25','unit_name':'L','unit_size':'1','bulk_price':'1.25'},
        'brand':'Hacendado',
        'categories':[{'name':'Lácteos'}],
        'thumbnail':'/img.jpg',
    }
    item.update(updates)
    return item


def test_dia_scrape_success_empty_and_failures(monkeypatch):
    scraper = DiaScraper(user_agent='ua', max_categories=2, delay_seconds=0)
    monkeypatch.setattr(scraper, 'get_category_paths', AsyncMock(return_value=['/a','/b','/c']))
    product = ScrapedProduct('Leche', Decimal('1.20'), 'DIA')
    monkeypatch.setattr(scraper, 'get_products_by_category', AsyncMock(side_effect=[([product],1),([],2)]))
    result = asyncio.run(scraper.scrape())
    assert result.status == 'success' and result.accepted_count == 1 and result.rejected_count == 3
    assert result.metadata['processed_categories'] == 2

    monkeypatch.setattr(scraper, 'get_category_paths', AsyncMock(return_value=[]))
    assert asyncio.run(scraper.scrape()).status == 'empty'

    monkeypatch.setattr(scraper, 'get_category_paths', AsyncMock(side_effect=ScraperBlockedError('blocked')))
    assert asyncio.run(scraper.scrape()).status == 'blocked'

    monkeypatch.setattr(scraper, 'get_category_paths', AsyncMock(side_effect=http_error(500)))
    failed = asyncio.run(scraper.scrape())
    assert failed.status == 'error' and '500' in failed.error

    monkeypatch.setattr(scraper, 'get_category_paths', AsyncMock(side_effect=RuntimeError('boom')))
    assert asyncio.run(scraper.scrape()).status == 'error'


def test_dia_get_categories_and_products(monkeypatch):
    scraper = DiaScraper(user_agent='ua', max_pages_per_category=3, delay_seconds=0)
    scraper.get_json = AsyncMock(return_value={
        'menu_analytics': {
            'one': {'path':' /leche/c/L1 ', 'children': {'a': {'parameter':'/arroz/c/L2'}}},
            'two': {'path':'/leche/c/L1'},
        }
    })
    assert asyncio.run(scraper.get_category_paths()) == ['/leche/c/L1','/arroz/c/L2']

    scraper.get_json = AsyncMock(return_value={'menu_analytics': []})
    assert asyncio.run(scraper.get_category_paths()) == []

    scraper.get_json = AsyncMock(side_effect=[{'plp_items':[valid_dia_item()]}, {'plp_items':[]}])
    products, rejected = asyncio.run(scraper.get_products_by_category('/leche/c/L1'))
    assert len(products) == 1 and rejected == 0

    scraper.get_json = AsyncMock(side_effect=http_error(404))
    assert asyncio.run(scraper.get_products_by_category('/x')) == ([],0)

    scraper.get_json = AsyncMock(side_effect=http_error(500))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(scraper.get_products_by_category('/x'))


def test_dia_parse_items_and_item_branches(monkeypatch):
    scraper = DiaScraper(user_agent='ua')
    invalid = {'name':'Sin precio'}
    broken = {'display_name':'x','price': object()}
    products, rejected = scraper._parse_items([valid_dia_item(), invalid, broken], category_path='/leche/c/L1')
    assert len(products) == 1 and rejected == 2

    with pytest.raises(ValueError, match='sin nombre'):
        scraper._parse_item({'price':1}, category_path='/x')
    with pytest.raises(ValueError, match='sin precio'):
        scraper._parse_item({'name':'Leche'}, category_path='/x')

    fallback = scraper._parse_item({
        'name':'Arroz', 'price':2, 'manufacturer':'Marca', 'prices_measure_unit':'kg',
        'prices_price_per_unit':'2', 'product_id':99, 'product_url':'https://x/p', 'image_url':'https://x/i'
    }, category_path='arroz/c/L2')
    assert fallback.marca == 'Marca' and fallback.formato == '2 €/kg' and fallback.external_id == '99'

    unit_only = scraper._parse_item({'title':'Agua','unit_price':1,'unit':'L','sku':'S','share_url':'agua','thumbnail':'img'}, category_path='/bebidas/c/L3')
    assert unit_only.formato == 'L' and unit_only.url_producto.endswith('/agua')

    explicit_format = scraper._parse_item({'name':'Pack','price':3,'format':'6 uds'}, category_path='/packs')
    assert explicit_format.formato == '6 uds'


def test_dia_helpers():
    scraper = DiaScraper(user_agent='ua', cookie='a=b')
    assert scraper._dia_headers()['Cookie'] == 'a=b'
    assert scraper._build_products_url('x?sort=a', page=2).endswith('&page=2')
    paths = scraper._extract_category_paths({'a':{'path':'/a','parameter':'/p','children':{'x':{'path':'/b'}}}, 'bad':'x'})
    assert paths == ['/a','/p','/b']
    assert scraper._extract_brand({'marca':'M'}) == 'M'
    assert scraper._extract_unit({'measure_unit':'kg'}) == 'kg'
    assert scraper._extract_format({'packaging':'caja'}) == 'caja'
    assert scraper._extract_external_id({}) is None
    assert scraper._absolute_url(None) is None
    assert scraper._absolute_url('https://x') == 'https://x'
    assert scraper._first_non_empty(None,' ','x') == 'x'
    assert scraper._category_name_from_path('') is None
    assert scraper._category_name_from_path('/c/L1') is None


def test_mercadona_scrape_success_empty_and_failures(monkeypatch):
    scraper = MercadonaScraper(user_agent='ua', max_categories=3, delay_seconds=0)
    monkeypatch.setattr(scraper, 'get_category_ids', AsyncMock(return_value=[1,2,3]))
    p = ScrapedProduct('Leche', Decimal('1.00'), 'Mercadona')
    monkeypatch.setattr(scraper, 'get_products_by_category', AsyncMock(side_effect=[([p],1,False),([],0,True),([],2,False)]))
    result = asyncio.run(scraper.scrape())
    assert result.status == 'success' and result.rejected_count == 3
    assert result.metadata['skipped_categories'] == 1

    monkeypatch.setattr(scraper, 'get_category_ids', AsyncMock(return_value=[]))
    assert asyncio.run(scraper.scrape()).status == 'empty'
    monkeypatch.setattr(scraper, 'get_category_ids', AsyncMock(side_effect=ScraperBlockedError('b')))
    assert asyncio.run(scraper.scrape()).status == 'blocked'
    monkeypatch.setattr(scraper, 'get_category_ids', AsyncMock(side_effect=http_error(503)))
    assert asyncio.run(scraper.scrape()).status == 'error'
    monkeypatch.setattr(scraper, 'get_category_ids', AsyncMock(side_effect=RuntimeError('x')))
    assert asyncio.run(scraper.scrape()).status == 'error'


def test_mercadona_get_category_ids_fallback(monkeypatch):
    scraper = MercadonaScraper(user_agent='ua')
    scraper.get_json = AsyncMock(side_effect=[http_error(500), {'categories':[{'id':1},{'id':2},{'id':2}]}])
    ids = asyncio.run(scraper.get_category_ids())
    assert ids == [1,2]
    assert scraper._active_endpoint_name == 'api_v1_1'

    scraper = MercadonaScraper(user_agent='ua')
    scraper.get_json = AsyncMock(return_value={'categories':[]})
    assert asyncio.run(scraper.get_category_ids()) == []


def test_mercadona_products_by_category(monkeypatch):
    scraper = MercadonaScraper(user_agent='ua')
    assert asyncio.run(scraper.get_products_by_category(1)) == ([],0,True)

    scraper._active_detail_url_template = 'https://x/{category_id}'
    scraper.get_json = AsyncMock(side_effect=http_error(404))
    assert asyncio.run(scraper.get_products_by_category(1)) == ([],0,True)
    scraper.get_json = AsyncMock(side_effect=http_error(500))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(scraper.get_products_by_category(1))

    scraper.get_json = AsyncMock(return_value={'products':[]})
    assert asyncio.run(scraper.get_products_by_category(1)) == ([],0,True)

    scraper.get_json = AsyncMock(return_value={'name':'Lácteos','products':[valid_merc_item(), {'display_name':'Sin precio'}, {'id':3}]})
    products, rejected, skipped = asyncio.run(scraper.get_products_by_category(1))
    assert len(products) == 1 and rejected == 2 and skipped is False


def test_mercadona_parse_product_branches():
    scraper = MercadonaScraper(user_agent='ua')
    scraper._active_endpoint_name = 'api'
    product = scraper._parse_product(valid_merc_item())
    assert product.nombre == 'Leche entera' and product.formato == '1 L · 1.25 €/L'
    assert product.url_producto.endswith('/product/10')

    with pytest.raises(ValueError, match='sin nombre'):
        scraper._parse_product({'price':1})
    with pytest.raises(ValueError, match='sin precio'):
        scraper._parse_product({'name':'Leche'})

    fallback = scraper._parse_product({
        'name':'Arroz','price':2,'manufacturer':'M','product_id':'X','url':'/arroz','image':'img',
        'unit_name':'kg','unit_size':'1','bulk_price':'2'
    }, fallback_category={'display_name':'Cereales'})
    assert fallback.categoria == 'Cereales' and fallback.marca == 'M'

    no_id = scraper._parse_product({'title':'Agua','price':1,'share_url':'relative'})
    assert no_id.url_producto == 'relative'


def test_mercadona_extractors_and_helpers():
    scraper = MercadonaScraper(user_agent='ua')
    data = {'results':[{'id':1,'children':[{'id':'2'}]}, {'id':3, 'display_name':'Producto'}]}
    assert scraper._extract_category_ids(data) == [2]
    assert scraper._extract_category_ids('bad') == []

    products = scraper._extract_products({'categories':{'children':[{'products':[{'id':1},'bad']}]}})
    assert products == [{'id':1}]

    assert scraper._extract_brand({'brand':' M '}) == 'M'
    assert scraper._extract_brand({}) is None
    assert scraper._extract_category_name({'categories':[{'display_name':'Bebidas'}]}, None) == 'Bebidas'
    assert scraper._extract_category_name({}, {'name':'General'}) == 'General'
    assert scraper._extract_category_name({}, None) is None
    assert scraper._extract_external_id({}) is None
    assert scraper._build_product_url({}, '/x').endswith('/x')
    assert scraper._absolute_url(None) is None
    assert scraper._absolute_url('https://x') == 'https://x'
    assert scraper._absolute_url('/x').endswith('/x')
    assert scraper._absolute_url('slug') == 'slug'
    assert scraper._build_format(unit_size=None, unit_name='kg', bulk_price=None) == 'kg'
    assert scraper._build_format(unit_size=None, unit_name=None, bulk_price='2') is None
    assert scraper._get_nested_category_nodes({'categories':{'id':1},'children':[{'id':2}], 'subcategories':'bad'}) == [{'id':1},{'id':2}]
    assert scraper._looks_like_product({'price_instructions':{}})
    assert scraper._parse_int_id(3) == 3 and scraper._parse_int_id('3') == 3 and scraper._parse_int_id('x') is None
    assert scraper._unique_ids([1,1,2]) == [1,2]
    assert scraper._first_non_empty(None,' ','x') == 'x'
