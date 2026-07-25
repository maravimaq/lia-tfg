from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas.chat import ListChatAIResponse, ListChatMessageRequest, ListChatSuggestion
from app.services.list_chatbot_service import ListChatbotService
import app.services.list_chatbot_service as module


def prod(pid, name, price, market, category='Lácteos', brand='Marca', unit='L'):
    return SimpleNamespace(
        id_producto=pid,
        nombre=name,
        precio_unitario=Decimal(str(price)),
        supermercado=market,
        categoria=category,
        marca=brand,
        unidad_medida=unit,
    )


def line(lid, product, qty, subtotal=None):
    return SimpleNamespace(
        id_producto_lista=lid,
        producto=product,
        cantidad=qty,
        precio_estimado=Decimal(str(subtotal if subtotal is not None else Decimal(str(product.precio_unitario)) * qty)),
    )


def test_process_message_builds_context_and_response(monkeypatch, db, user):
    original = prod(1, 'Leche entera', 1.50, 'DIA')
    lista = SimpleNamespace(
        id_lista=7,
        nombre_lista='Compra semanal',
        total_estimado=Decimal('3.00'),
        productos=[line(10, original, 2)],
    )
    monkeypatch.setattr(module.ListaCompraService, 'get_lista_detalle', MagicMock(return_value=lista))
    monkeypatch.setattr(module.ProductoRepository, 'get_all', MagicMock(return_value=[original]))
    monkeypatch.setattr(module.AnalyticsService, 'build_chatbot_analytics_context', MagicMock(return_value={'ok': True}))
    monkeypatch.setattr(
        module.ListChatbotAIService,
        'generate_response',
        MagicMock(return_value=ListChatAIResponse(
            intent='analizar_lista',
            reply='Todo correcto',
            suggestions=[ListChatSuggestion(type='info', title='Dato', description='Bien')],
            confidence=0.91,
        )),
    )
    monkeypatch.setattr(module.settings, 'ai_provider', 'mock')

    result = ListChatbotService.process_message(db, 7, ListChatMessageRequest(message=' analiza '), user)

    assert result.reply == 'Todo correcto'
    assert result.context_summary['lista_id'] == 7
    assert result.context_summary['num_productos'] == 1
    assert result.context_summary['provider'] == 'mock'
    sent_context = module.ListChatbotAIService.generate_response.call_args.kwargs['list_context']
    assert sent_context['historico_usuario'] == {'ok': True}


def test_build_context_full_comparisons(monkeypatch, db, user):
    leche = prod(1, 'Leche entera', 1.50, 'DIA')
    leche_mercadona = prod(2, 'Leche entera fresca', 1.00, 'Mercadona')
    leche_carrefour = prod(3, 'Leche entera', 1.20, 'Carrefour')
    arroz = prod(4, 'Arroz redondo', 2.00, 'DIA', category='Arroz', unit='kg')
    arroz_mercadona = prod(5, 'Arroz redondo', 1.50, 'Mercadona', category='Arroz', unit='kg')
    orphan = SimpleNamespace(id_producto_lista=99, producto=None, cantidad=1, precio_estimado=1)
    lista = SimpleNamespace(
        id_lista=9,
        nombre_lista='Lista completa',
        total_estimado=Decimal('9.00'),
        productos=[line(1, leche, 2, 3), line(2, arroz, 3, 6), orphan],
    )
    monkeypatch.setattr(
        module.ProductoRepository,
        'get_all',
        MagicMock(return_value=[leche, leche_mercadona, leche_carrefour, arroz, arroz_mercadona]),
    )
    monkeypatch.setattr(module.AnalyticsService, 'build_chatbot_analytics_context', MagicMock(return_value={'monthly': []}))

    ctx = ListChatbotService._build_list_context(db, lista, user)

    analysis = ctx['analisis_precalculado']
    assert analysis['num_productos'] == 2
    assert len(analysis['candidatos_ahorro']) == 2
    assert analysis['comparativa_por_producto'][0]['tiene_ahorro'] is True
    assert analysis['comparativa_cesta_equivalente']['mejor_cesta_completa']['supermercado'] == 'Mercadona'
    assert ctx['totales_actuales_por_supermercado']['DIA'] == 9.0
    assert analysis['productos_con_cantidad_alta'][0]['nombre'] == 'Arroz redondo'
    assert analysis['categorias_resumen'][0]['subtotal'] == 6.0
    assert ctx['historico_usuario'] == {'monthly': []}


def test_build_context_without_user_or_products(db):
    lista = SimpleNamespace(id_lista=1, nombre_lista='Vacía', total_estimado=0, productos=[])
    ctx = ListChatbotService._build_list_context(db, lista, None)
    basket = ctx['analisis_precalculado']['comparativa_cesta_equivalente']
    assert basket['total_productos_lista'] == 0
    assert basket['mejor_cesta_completa'] is None
    assert ctx['historico_usuario'] is None


def test_get_equivalents_orders_original_and_filters(monkeypatch, db):
    original = prod(1, 'Leche entera', 1.50, 'DIA')
    good = prod(2, 'Leche entera fresca', 1.00, 'Mercadona')
    bad = prod(3, 'Galletas chocolate', 0.50, 'Mercadona', category='Dulces')
    monkeypatch.setattr(module.ProductoRepository, 'get_all', MagicMock(return_value=[bad, good, original]))

    result = ListChatbotService._get_equivalent_products_for_product(db, original)
    alternatives = ListChatbotService._get_alternatives_for_product(db, original)

    assert [x.id_producto for x in result] == [1, 2]
    assert [x.id_producto for x in alternatives] == [2]


def test_equivalent_context_keeps_cheapest_per_market():
    original = prod(1, 'Leche entera', 1.50, 'DIA')
    expensive = prod(2, 'Leche entera', 1.40, 'Mercadona')
    cheap = prod(3, 'Leche fresca', 1.00, 'Mercadona')
    ctx = ListChatbotService._build_equivalent_product_context(line(1, original, 2, 3), original, [original, expensive, cheap])
    assert ctx['opciones_por_supermercado']['Mercadona']['producto_id'] == 3
    assert ctx['opciones_por_supermercado']['Mercadona']['subtotal_estimado'] == 2.0


def test_product_level_comparison_edge_cases():
    original = prod(1, 'Leche entera', 1.50, 'DIA')
    same_market = prod(2, 'Leche entera fresca', 1.00, 'DIA')
    other_expensive = prod(3, 'Leche entera premium', 2.00, 'Mercadona')

    assert ListChatbotService._build_product_level_comparison(line(1, original, 0, 0), original, [other_expensive]) is None
    assert ListChatbotService._build_product_level_comparison(line(1, original, 1, 1.5), original, [same_market]) is None

    result = ListChatbotService._build_product_level_comparison(
        line(1, original, 2, 3), original, [other_expensive, other_expensive, original]
    )
    assert result['tiene_ahorro'] is False
    assert len(result['opciones_comparables']) == 2


def test_equivalent_basket_complete_partial_and_empty_options():
    entries = [
        {
            'producto_original': {'nombre': 'Leche'},
            'cantidad': 2,
            'opciones_por_supermercado': {
                'DIA': {'nombre': 'Leche DIA', 'producto_id': 1, 'subtotal_estimado': 2, 'precio_unitario': 1, 'unidad_medida': 'L'},
                'Mercadona': {'nombre': 'Leche M', 'producto_id': 2, 'subtotal_estimado': 1.8, 'precio_unitario': .9, 'unidad_medida': 'L'},
            },
        },
        {
            'producto_original': {'nombre': 'Arroz'},
            'cantidad': 1,
            'opciones_por_supermercado': {
                'DIA': {'nombre': 'Arroz DIA', 'producto_id': 3, 'subtotal_estimado': 2, 'precio_unitario': 2, 'unidad_medida': 'kg'},
            },
        },
    ]
    result = ListChatbotService._build_equivalent_basket_comparison(entries)
    assert result['mejor_cesta_completa']['supermercado'] == 'DIA'
    assert result['cestas_parciales'][0]['supermercado'] == 'Mercadona'
    assert result['cestas_parciales'][0]['productos_no_encontrados'] == ['Arroz']

    no_options = ListChatbotService._build_equivalent_basket_comparison([
        {'producto_original': {'nombre': 'X'}, 'cantidad': 1, 'opciones_por_supermercado': {}}
    ])
    assert no_options['ranking'] == []


def test_score_additional_branches():
    unknown_a = prod(1, 'Producto alfa común', 1, 'DIA', category='Misma')
    unknown_b = prod(2, 'Producto alfa común premium', 1, 'Mercadona', category='Misma')
    different_category = prod(3, 'Producto alfa común', 1, 'Mercadona', category='Otra')
    chocolate = prod(4, 'Galletas chocolate', 1, 'DIA', category='Dulces')
    no_chocolate = prod(5, 'Galletas vainilla', 1, 'Mercadona', category='Dulces')
    family_missing = prod(6, 'Alimento chocolate especial', 1, 'Mercadona', category='Dulces')

    assert ListChatbotService._score_product_alternative(unknown_a, unknown_b) >= 75
    assert ListChatbotService._score_product_alternative(unknown_a, different_category) == 0
    assert ListChatbotService._score_product_alternative(chocolate, no_chocolate) > 0
    assert ListChatbotService._score_product_alternative(chocolate, family_missing) == 0
