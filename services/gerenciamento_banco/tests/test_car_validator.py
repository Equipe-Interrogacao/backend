import pytest

from app.utils.car_validator import (
    FormatoCarInvalidoError,
    normalizar_codigo_car,
    validar_codigo_car,
)

_CAR_FED_OK = "SP-3525300-44AA2FE43D774264B9F18E55658E70FA"


def test_validar_car_numerico_11_digitos():
    assert validar_codigo_car("12345678901") == "12345678901"


def test_validar_car_numerico_17_digitos_tipico():
    c = "35253000000167"
    assert validar_codigo_car(c) == c


def test_validar_car_numerico_com_espacos():
    assert validar_codigo_car("  35253000000167  ") == "35253000000167"


def test_validar_car_federal_maiusculo():
    assert validar_codigo_car(_CAR_FED_OK) == _CAR_FED_OK


def test_validar_car_federal_normaliza_uf():
    lower = "sp-3525300-44aa2fe43d774264b9f18e55658e70fa"
    out = validar_codigo_car(lower)
    assert out.startswith("SP-")


def test_invalido_vazio():
    with pytest.raises(FormatoCarInvalidoError):
        validar_codigo_car("")


def test_invalido_so_espacos():
    with pytest.raises(FormatoCarInvalidoError):
        validar_codigo_car("   ")


def test_invalido_curto_numerico():
    with pytest.raises(FormatoCarInvalidoError):
        validar_codigo_car("1234567890")  # 10 dígitos


def test_invalido_longo_numerico():
    with pytest.raises(FormatoCarInvalidoError):
        validar_codigo_car("1" * 21)


def test_invalido_texto_aleatorio():
    with pytest.raises(FormatoCarInvalidoError):
        validar_codigo_car("abc-def-ghi")


def test_invalido_federal_hex_curto():
    with pytest.raises(FormatoCarInvalidoError):
        validar_codigo_car("SP-3525300-44AA")


def test_normalizar_none():
    with pytest.raises(FormatoCarInvalidoError):
        normalizar_codigo_car(None)  # type: ignore[arg-type]
