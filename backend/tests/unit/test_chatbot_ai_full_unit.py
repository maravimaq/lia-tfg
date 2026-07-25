from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.chat import ListChatAIResponse, ListChatSuggestion
from app.services.chatbot_ai_service import ListChatbotAIService
import app.services.chatbot_ai_service as module


def ai_response(**kwargs):
    data = {
        'intent': 'pregunta_general_lista',
        'reply': 'Esta es una respuesta concreta, suficientemente extensa y basada en los productos reales de la lista.',
        'suggestions': [ListChatSuggestion(type='info', title='Dato', description='Información útil')],
        'confidence': 0.92,
    }
    data.update(kwargs)
    return ListChatAIResponse(**data)


def context():
    return {
        'lista': {'nombre_lista': 'Compra', 'total_estimado': 20},
        'productos': [
            {'nombre': 'Leche', 'categoria': 'Lácteos', 'cantidad': 2, 'precio_estimado': 3},
            {'nombre': 'Chocolate', 'categoria': 'Dulces', 'cantidad': 1, 'precio_estimado': 4},
        ],
        'historico_usuario': {},
        'analisis_precalculado': {
            'desglose_supermercados_actual': [{'supermercado': 'DIA', 'total': 20}],
            'productos_mayor_peso_coste': [{'nombre': 'Chocolate', 'precio_estimado': 4, 'peso_en_total_porcentaje': 20}],
            'productos_con_cantidad_alta': [],
            'candidatos_ahorro': [],
            'comparativa_por_producto': [],
        },
    }


def fake_http_client(monkeypatch, *, json_data=None, post_error=None, raise_error=None):
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status.side_effect = raise_error
    client = MagicMock()
    client.post.side_effect = post_error
    if post_error is None:
        client.post.return_value = response
    manager = MagicMock()
    manager.__enter__.return_value = client
    manager.__exit__.return_value = False
    monkeypatch.setattr(module.httpx, 'Client', MagicMock(return_value=manager))
    return client, response


def valid_json(reply=None):
    return {
        'intent': 'pregunta_general_lista',
        'reply': reply or 'Respuesta concreta y suficientemente extensa para superar el filtro de calidad del asistente.',
        'suggestions': [{'type': 'info', 'title': 'Dato', 'description': 'Detalle'}],
        'confidence': 0.95,
    }


def test_generate_response_routes_to_ollama_and_openai(monkeypatch):
    monkeypatch.setattr(ListChatbotAIService, '_should_answer_deterministically', MagicMock(return_value=False))
    ollama = MagicMock(return_value=ai_response())
    openai = MagicMock(return_value=ai_response())
    monkeypatch.setattr(ListChatbotAIService, '_generate_with_ollama', ollama)
    monkeypatch.setattr(ListChatbotAIService, '_generate_with_openai', openai)

    monkeypatch.setattr(module.settings, 'ai_provider', ' OLLAMA ')
    ListChatbotAIService.generate_response(user_message='hola', list_context={})
    ollama.assert_called_once()

    monkeypatch.setattr(module.settings, 'ai_provider', 'openai')
    ListChatbotAIService.generate_response(user_message='hola', list_context={})
    openai.assert_called_once()


def test_generate_response_deterministic_precedes_provider(monkeypatch):
    monkeypatch.setattr(module.settings, 'ai_provider', 'ollama')
    fallback = MagicMock(return_value=ai_response(intent='analizar_lista'))
    monkeypatch.setattr(ListChatbotAIService, '_generate_mock_response', fallback)
    result = ListChatbotAIService.generate_response(user_message='analiza la lista', list_context=context())
    assert result.intent == 'analizar_lista'


def test_ollama_success(monkeypatch):
    monkeypatch.setattr(module.settings, 'ollama_model', 'model')
    monkeypatch.setattr(module.settings, 'ollama_base_url', 'http://localhost:11434/')
    monkeypatch.setattr(module.settings, 'ollama_timeout_seconds', 10)
    _, response = fake_http_client(monkeypatch, json_data={'message': {'content': __import__('json').dumps(valid_json())}})
    result = ListChatbotAIService._generate_with_ollama('hola', context())
    assert result.confidence == .95
    response.raise_for_status.assert_called_once()


def test_ollama_markdown_json_and_postprocess(monkeypatch):
    raw = '```json\n' + __import__('json').dumps(valid_json()) + '\n```'
    fake_http_client(monkeypatch, json_data={'message': {'content': raw}})
    result = ListChatbotAIService._generate_with_ollama('hola', context())
    assert result.suggestions


def test_ollama_connection_http_and_generic_errors(monkeypatch):
    request = httpx.Request('POST', 'http://ollama/api/chat')
    fake_http_client(monkeypatch, post_error=httpx.ConnectError('down', request=request))
    with pytest.raises(HTTPException) as exc:
        ListChatbotAIService._generate_with_ollama('hola', {})
    assert exc.value.status_code == 503

    response = httpx.Response(500, request=request, text='boom')
    fake_http_client(monkeypatch, raise_error=httpx.HTTPStatusError('bad', request=request, response=response))
    with pytest.raises(HTTPException) as exc:
        ListChatbotAIService._generate_with_ollama('hola', {})
    assert exc.value.status_code == 502 and 'boom' in exc.value.detail

    fake_http_client(monkeypatch, post_error=httpx.ReadError('read', request=request))
    with pytest.raises(HTTPException) as exc:
        ListChatbotAIService._generate_with_ollama('hola', {})
    assert exc.value.status_code == 502


def test_ollama_empty_and_invalid_schema(monkeypatch):
    fake_http_client(monkeypatch, json_data={'message': {}})
    with pytest.raises(HTTPException, match='contenido'):
        ListChatbotAIService._generate_with_ollama('hola', {})

    invalid = {'intent': 'no-existe', 'reply': 'x', 'suggestions': [], 'confidence': 2}
    fake_http_client(monkeypatch, json_data={'message': {'content': __import__('json').dumps(invalid)}})
    with pytest.raises(HTTPException, match='respuesta válida'):
        ListChatbotAIService._generate_with_ollama('hola', {})


def test_openai_configuration_errors(monkeypatch):
    monkeypatch.setattr(module, 'settings', SimpleNamespace(openai_enabled=False, openai_api_key=None, openai_timeout_seconds=10, openai_model='gpt'))
    with pytest.raises(HTTPException, match='desactivado'):
        ListChatbotAIService._generate_with_openai('hola', {})

    module.settings.openai_enabled = True
    module.settings.openai_api_key = None
    with pytest.raises(HTTPException, match='OPENAI_API_KEY'):
        ListChatbotAIService._generate_with_openai('hola', {})

    module.settings.openai_api_key = 'key'
    monkeypatch.setattr(module, 'OpenAI', None)
    with pytest.raises(HTTPException, match='dependencia openai'):
        ListChatbotAIService._generate_with_openai('hola', {})


def install_fake_openai(monkeypatch, *, parsed=None, error=None):
    parse = MagicMock(side_effect=error)
    if error is None:
        parse.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))])
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=parse)))
    factory = MagicMock(return_value=fake_client)
    monkeypatch.setattr(module, 'OpenAI', factory)
    monkeypatch.setattr(module, 'settings', SimpleNamespace(openai_enabled=True, openai_api_key='key', openai_timeout_seconds=10, openai_model='gpt'))
    return parse


def test_openai_success_and_none(monkeypatch):
    parsed = ai_response()
    parse = install_fake_openai(monkeypatch, parsed=parsed)
    result = ListChatbotAIService._generate_with_openai('hola', context())
    assert result.reply == parsed.reply
    assert parse.call_args.kwargs['response_format'] is ListChatAIResponse

    install_fake_openai(monkeypatch, parsed=None)
    with pytest.raises(HTTPException, match='estructurada'):
        ListChatbotAIService._generate_with_openai('hola', context())


def test_openai_provider_and_validation_errors(monkeypatch):
    install_fake_openai(monkeypatch, error=module.OpenAIError('api'))
    with pytest.raises(HTTPException, match='OpenAI'):
        ListChatbotAIService._generate_with_openai('hola', {})

    validation_error = ValidationError.from_exception_data('ListChatAIResponse', [])
    install_fake_openai(monkeypatch, error=validation_error)
    with pytest.raises(HTTPException, match='respuesta válida'):
        ListChatbotAIService._generate_with_openai('hola', {})


def test_postprocess_low_weak_and_original(monkeypatch):
    fallback = ai_response(intent='analizar_lista', confidence=.8)
    monkeypatch.setattr(ListChatbotAIService, '_generate_mock_response', MagicMock(return_value=fallback))
    low = ai_response(reply='La lista incluye productos')
    assert ListChatbotAIService._postprocess_response(ai_response=low, user_message='hola', list_context={}) is fallback

    weak = ai_response(reply='breve', suggestions=[], confidence=.5)
    assert ListChatbotAIService._postprocess_response(ai_response=weak, user_message='hola', list_context={}) is fallback

    strong_ai = ai_response(reply='breve', suggestions=[], confidence=.95)
    weak_fallback = ai_response(confidence=.5)
    monkeypatch.setattr(ListChatbotAIService, '_generate_mock_response', MagicMock(return_value=weak_fallback))
    monkeypatch.setattr(ListChatbotAIService, '_build_default_suggestion', MagicMock(return_value=None))
    assert ListChatbotAIService._postprocess_response(ai_response=strong_ai, user_message='hola', list_context={}) is strong_ai


def test_low_value_actionable_is_allowed():
    good = ai_response(
        reply='Revisaría este producto para ahorrar porque sale caro.',
        suggestions=[ListChatSuggestion(type='saving', title='Ahorro', description='Cambia')],
    )
    assert not ListChatbotAIService._is_low_value_response(good, 'analiza mi lista', {})


def comparison(ahorro=1.0):
    return {
        'tiene_ahorro': ahorro > 0,
        'producto_original': {'nombre': 'Leche', 'cantidad': 2, 'supermercado': 'DIA', 'precio_unitario': 1.5, 'subtotal': 3},
        'mejor_alternativa_otro_supermercado': {'nombre': 'Leche fresca', 'supermercado': 'Mercadona', 'precio_unitario': 1, 'subtotal_estimado': 2, 'ahorro_estimado': ahorro},
    }


def test_mock_response_routes_all_builders():
    ctx = context()
    ctx['analisis_precalculado']['comparativa_por_producto'] = [comparison(1)]
    assert ListChatbotAIService._generate_mock_response('dónde está más barata', ctx).intent == 'comparar_lista_supermercados'
    assert ListChatbotAIService._generate_mock_response('quiero ahorrar', ctx).intent == 'sugerir_ahorro'
    assert ListChatbotAIService._generate_mock_response('revisa cantidad kg', ctx).intent == 'recomendar_cantidad'
    assert ListChatbotAIService._generate_mock_response('cuánta pasta para 2 personas', ctx).intent == 'recomendar_cantidad'
    assert ListChatbotAIService._generate_mock_response('hay demasiado', ctx).intent == 'detectar_excesos'
    assert ListChatbotAIService._generate_mock_response('hola', ctx).intent == 'analizar_lista'


def test_supermarket_neutral_and_format_branches():
    neutral = ListChatbotAIService._build_supermarket_comparison_response({'comparativa_por_producto': [comparison(-1)]})
    assert neutral.confidence == .78
    assert neutral.suggestions[0].type == 'info'

    original = comparison()['producto_original']
    alt = comparison(0)['mejor_alternativa_otro_supermercado']
    assert 'prácticamente igual' in ListChatbotAIService._format_product_level_comparison(original=original, alternative=alt)
    alt['ahorro_estimado'] = -2
    assert 'más caro' in ListChatbotAIService._format_product_level_comparison(original=original, alternative=alt)

    assert 'DIA' in ListChatbotAIService._format_equivalent_basket_ranking([{'supermercado':'DIA','total_estimado':2}])
    assert '1/2' in ListChatbotAIService._format_partial_basket_ranking([{'supermercado':'DIA','total_estimado':2,'productos_encontrados':1,'productos_totales':2}])
    assert ListChatbotAIService._format_current_supermarket_breakdown({}) == 'sin desglose disponible'
    assert 'DIA' in ListChatbotAIService._format_current_supermarket_breakdown({'desglose_supermercados_actual':[{'supermercado':'DIA','total':2}]})


def test_saving_response_three_paths():
    by_comparison = ListChatbotAIService._build_saving_response({'comparativa_por_producto':[comparison(1)]})
    assert by_comparison.suggestions[0].type == 'saving'

    empty = ListChatbotAIService._build_saving_response({})
    assert empty.suggestions == []

    candidate = ListChatbotAIService._build_saving_response({'candidatos_ahorro':[{
        'producto_original':'Leche','alternativa':'Leche barata','supermercado_alternativa':'DIA',
        'precio_alternativa':1,'ahorro_estimado':2,
    }]})
    assert 'Leche barata' in candidate.reply


def insight(**updates):
    data = {
        'producto_actual':'Leche entera', 'familia_detectada':'leche', 'categoria':'lácteos',
        'cantidad_actual':2, 'cantidad_media_mensual':8, 'cantidad_media_por_compra':2,
        'cantidad_total_mes_actual':3, 'cantidad_esperada_restante_mes':5,
        'porcentaje_mes_transcurrido':40, 'recomendacion_orientativa':'Mantén la cantidad.',
        'compras_historicas':4, 'unidad_medida':'L',
    }
    data.update(updates)
    return data


def test_historical_quantity_paths():
    assert ListChatbotAIService._build_historical_quantity_response(message='leche', historico_usuario={}) is None
    assert ListChatbotAIService._build_historical_quantity_response(message='sin coincidencia', historico_usuario={'productos_relevantes':[insight(), insight(producto_actual='Arroz', familia_detectada='arroz')]}) is None
    assert ListChatbotAIService._build_historical_quantity_response(message='leche', historico_usuario={'productos_relevantes':[insight(compras_historicas=0)]}) is None

    result = ListChatbotAIService._build_historical_quantity_response(message='cuánta leche', historico_usuario={'productos_relevantes':[insight()]})
    assert '8 L al mes' in result.reply and '5 L' in result.reply

    no_optional = ListChatbotAIService._build_historical_quantity_response(message='leche', historico_usuario={'productos_relevantes':[insight(cantidad_media_por_compra=None, cantidad_esperada_restante_mes=None)]})
    assert no_optional is not None


def test_select_historical_by_family_category_token_and_single():
    a = insight(producto_actual='Leche entera', familia_detectada='leche', categoria='lácteos')
    b = insight(producto_actual='Arroz redondo', familia_detectada='arroz', categoria='cereales')
    assert ListChatbotAIService._select_relevant_historical_insight('cuánta leche', [a,b]) is a
    assert ListChatbotAIService._select_relevant_historical_insight('cereales', [a,b]) is b
    assert ListChatbotAIService._select_relevant_historical_insight('nada', [a]) is a
    assert ListChatbotAIService._select_relevant_historical_insight('nada', [a,b]) is None


def test_quantity_review_four_paths():
    high = ListChatbotAIService._build_quantity_review_response({'productos_con_cantidad_alta':[{'nombre':'Leche','cantidad':5,'precio_estimado':7}]}, [])
    assert 'Leche' in high.reply

    sweets = ListChatbotAIService._build_quantity_review_response({}, [{'nombre':'Galletas','categoria':'Dulces'},{'nombre':'Chocolate','categoria':'Dulces'}])
    assert 'concentrada' in sweets.reply

    top = ListChatbotAIService._build_quantity_review_response({'productos_mayor_peso_coste':[{'nombre':'Aceite','precio_estimado':8}]}, [])
    assert 'Aceite' in top.reply

    empty = ListChatbotAIService._build_quantity_review_response({}, [])
    assert empty.suggestions == []


def test_quantity_response_three_paths():
    assert 'Para 3 personas' in ListChatbotAIService._build_quantity_response('pasta para 3 personas', []).reply
    products = [{'nombre':'Leche entera','cantidad':2}]
    assert '2 unidades' in ListChatbotAIService._build_quantity_response('cuánta leche', products).reply
    assert '80-100 g' in ListChatbotAIService._build_quantity_response('cuánta cantidad', []).reply


def test_excess_and_default_suggestion_edge_paths():
    high = ListChatbotAIService._build_excess_response({'productos_con_cantidad_alta':[{'nombre':'Leche','cantidad':4}]})
    assert high.suggestions
    empty = ListChatbotAIService._build_excess_response({})
    assert empty.suggestions == []

    assert ListChatbotAIService._build_default_suggestion('hola', {}) is None
    ctx = context()
    assert ListChatbotAIService._build_default_suggestion('hola', ctx) is not None


def test_find_relevant_no_tokens_and_plural_invalid():
    assert ListChatbotAIService._find_relevant_product_in_list('a y de', [{'nombre':'Leche'}]) is None
    assert ListChatbotAIService._plural('bad', 'uno', 'varios') == '0 varios'
