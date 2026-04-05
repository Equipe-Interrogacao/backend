import pytest
from unittest.mock import MagicMock

from app.models.imovel import Imovel
from app.services.imovel_service import ImovelService
from app.utils.car_validator import FormatoCarInvalidoError


def _chain_query_first(result):
    db = MagicMock()
    first = MagicMock(return_value=result)
    filt = MagicMock()
    filt.first = first
    q = MagicMock()
    q.filter.return_value = filt
    db.query.return_value = q
    return db, q, filt, first


def test_buscar_por_car_invalido():
    db = MagicMock()
    svc = ImovelService()
    with pytest.raises(FormatoCarInvalidoError):
        svc.buscar_por_car(db, "123")


def test_buscar_por_car_nao_encontrado():
    db, _, _, _ = _chain_query_first(None)
    svc = ImovelService()
    assert svc.buscar_por_car(db, "35253000000167") is None
    db.query.assert_called_once_with(Imovel)


def test_buscar_por_car_encontrado():
    imovel = Imovel(
        id=1,
        codigo_car="35253000000167",
        area_ha=10.5,
        municipio="JAÚ",
        situacao="Inscrito",
        dt_inscricao=None,
        dt_analise=None,
        geometria=None,
    )
    db, _, _, _ = _chain_query_first(imovel)
    svc = ImovelService()
    out = svc.buscar_por_car(db, "35253000000167")
    assert out is imovel
