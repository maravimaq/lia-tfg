import pytest
from pydantic import ValidationError

from app.schemas.preferences import PreferenciasBase, PreferenciasUpdate


def test_preferencias_normalizan_valores():
    prefs = PreferenciasBase(
        idioma=" EN ",
        unidad_peso=" LB ",
        unidad_precio="usd",
        supermercado_favorito="día",
    )

    assert prefs.idioma == "en"
    assert prefs.unidad_peso == "lb"
    assert prefs.unidad_precio == "USD"
    assert prefs.supermercado_favorito == "DIA"


def test_supermercado_vacio_se_convierte_en_none():
    assert PreferenciasUpdate(supermercado_favorito="  ").supermercado_favorito is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"idioma": "fr"},
        {"unidad_peso": "ton"},
        {"unidad_precio": "GBP"},
        {"supermercado_favorito": "Lidl"},
    ],
)
def test_preferencias_rechazan_opciones_no_soportadas(kwargs):
    with pytest.raises(ValidationError):
        PreferenciasBase(**kwargs)
