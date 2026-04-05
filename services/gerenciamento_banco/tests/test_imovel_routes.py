from datetime import datetime, timezone
from unittest.mock import MagicMock

from sqlalchemy.exc import SQLAlchemyError

from app.models.imovel import Imovel


def _setup_query_mock(mock_db: MagicMock, first_result):
    filt = MagicMock()
    filt.first.return_value = first_result
    q = MagicMock()
    q.filter.return_value = filt
    mock_db.query.return_value = q


def test_get_imovel_400(client: MagicMock, mock_db: MagicMock):
    r = client.get("/imovel", params={"car": "abc"})
    assert r.status_code == 400
    assert "inválido" in r.json()["detail"].lower() or "CAR" in r.json()["detail"]


def test_get_imovel_404(client: MagicMock, mock_db: MagicMock):
    _setup_query_mock(mock_db, None)
    r = client.get("/imovel", params={"car": "35253000000167"})
    assert r.status_code == 404


def test_get_imovel_200(client: MagicMock, mock_db: MagicMock):
    imovel = Imovel(
        id=1,
        codigo_car="35253000000167",
        area_ha=12.3,
        municipio="JAÚ",
        situacao="Inscrito",
        dt_inscricao=datetime(2019, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        dt_analise=None,
        geometria=None,
    )
    _setup_query_mock(mock_db, imovel)
    r = client.get("/imovel", params={"car": "35253000000167"})
    assert r.status_code == 200
    body = r.json()
    assert body["codigo_car"] == "35253000000167"
    assert body["area_ha"] == 12.3
    assert body["municipio"] == "JAÚ"
    assert body["situacao"] == "Inscrito"
    assert body["dt_analise"] is None


def test_get_imovel_500(client: MagicMock, mock_db: MagicMock):
    mock_db.query.side_effect = SQLAlchemyError("fail")
    r = client.get("/imovel", params={"car": "35253000000167"})
    assert r.status_code == 500
