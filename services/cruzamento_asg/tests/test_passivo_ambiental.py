"""
Testes do endpoint GET /cruzamento/car/{cod_imovel}/passivos-ambientais.

Usa mocks para o client HTTP (ingestao) e para a sessao do banco,
permitindo rodar sem PostGIS real.
"""

import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

POLIGONO_SP = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [
                [-46.65, -23.55],
                [-46.64, -23.55],
                [-46.64, -23.54],
                [-46.65, -23.54],
                [-46.65, -23.55],
            ]
        ]
    ],
}

COD_IMOVEL = "SP-3550308-XXXXXXXXX"


def _fake_row(fonte, tipo_alerta, data_ref, area_ha, geom_json=None):
    row = MagicMock()
    row.fonte = fonte
    row.tipo_alerta = tipo_alerta
    row.data_referencia = data_ref
    row.area_ha = area_ha
    row.geometria_intersecao = json.dumps(geom_json) if geom_json else None
    return row


@pytest.fixture
def mock_ingestao_found():
    with patch(
        "app.controllers.passivo_controller.buscar_geometria_propriedade",
        new_callable=AsyncMock,
        return_value=POLIGONO_SP,
    ) as m:
        yield m


@pytest.fixture
def mock_ingestao_not_found():
    with patch(
        "app.controllers.passivo_controller.buscar_geometria_propriedade",
        new_callable=AsyncMock,
        return_value=None,
    ) as m:
        yield m


@pytest.fixture
def mock_db_with_results():
    rows = [
        _fake_row("deter", "DESMATAMENTO_CR", date(2023, 6, 15), 2.5431),
        _fake_row("deter", "DEGRADACAO", date(2023, 8, 1), 0.8712),
    ]

    mock_session = MagicMock()
    mock_session.execute.return_value.fetchall.return_value = rows

    with patch("app.routes.passivo_routes.get_db", return_value=iter([mock_session])):
        yield mock_session


@pytest.fixture
def mock_db_empty():
    mock_session = MagicMock()
    mock_session.execute.return_value.fetchall.return_value = []

    with patch("app.routes.passivo_routes.get_db", return_value=iter([mock_session])):
        yield mock_session


class TestPassivosAmbientais:
    def test_propriedade_nao_encontrada_retorna_404(self, mock_ingestao_not_found):
        """cod_imovel invalido deve retornar HTTP 404."""
        mock_session = MagicMock()
        with patch(
            "app.routes.passivo_routes.get_db", return_value=iter([mock_session])
        ):
            resp = client.get(f"/cruzamento/car/{COD_IMOVEL}/passivos-ambientais")
            assert resp.status_code == 404
            assert "nao encontrada" in resp.json()["detail"]

    def test_sem_sobreposicao_retorna_200_lista_vazia(
        self, mock_ingestao_found, mock_db_empty
    ):
        """Propriedade sem alertas deve retornar 200 com lista vazia."""
        resp = client.get(f"/cruzamento/car/{COD_IMOVEL}/passivos-ambientais")
        assert resp.status_code == 200

        body = resp.json()
        assert body["cod_imovel"] == COD_IMOVEL
        assert body["total_alertas"] == 0
        assert body["area_total_passivos_ha"] == 0.0
        assert body["passivos"] == []

    def test_com_sobreposicao_retorna_alertas(
        self, mock_ingestao_found, mock_db_with_results
    ):
        """Cruzamento com dados DETER deve retornar passivos com area."""
        resp = client.get(
            f"/cruzamento/car/{COD_IMOVEL}/passivos-ambientais?fonte=deter"
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["total_alertas"] == 2
        assert body["area_total_passivos_ha"] > 0

        passivo = body["passivos"][0]
        assert passivo["fonte"] == "deter"
        assert passivo["tipo_alerta"] == "DESMATAMENTO_CR"
        assert passivo["area_ha"] == 2.5431

    def test_filtro_por_data(self, mock_ingestao_found, mock_db_empty):
        """Query com data_inicio e data_fim deve ser aceita (HTTP 200)."""
        resp = client.get(
            f"/cruzamento/car/{COD_IMOVEL}/passivos-ambientais"
            "?data_inicio=2023-01-01&data_fim=2024-12-31"
        )
        assert resp.status_code == 200

    def test_filtro_fonte_invalida_ignora(self, mock_ingestao_found, mock_db_empty):
        """Fonte inexistente no enum eh silenciosamente ignorada."""
        resp = client.get(
            f"/cruzamento/car/{COD_IMOVEL}/passivos-ambientais?fonte=invalida"
        )
        assert resp.status_code == 200

    def test_multiplas_fontes(self, mock_ingestao_found, mock_db_empty):
        """Fontes separadas por virgula sao parseadas corretamente."""
        resp = client.get(
            f"/cruzamento/car/{COD_IMOVEL}/passivos-ambientais?fonte=deter,prodes,queimadas"
        )
        assert resp.status_code == 200

    def test_data_referencia_prodes_inteiro(self, mock_ingestao_found):
        """PRODES retorna ano (int) que deve ser convertido para date."""
        rows = [_fake_row("prodes", "DESMATAMENTO", 2022, 10.0)]

        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = rows

        with patch(
            "app.routes.passivo_routes.get_db", return_value=iter([mock_session])
        ):
            resp = client.get(
                f"/cruzamento/car/{COD_IMOVEL}/passivos-ambientais?fonte=prodes"
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["total_alertas"] == 1
            assert body["passivos"][0]["data_referencia"] == "2022-01-01"

    def test_data_referencia_datetime(self, mock_ingestao_found):
        """Queimadas retorna datetime que deve ser convertido para date."""
        rows = [_fake_row("queimadas", "AQUA_M-T", datetime(2023, 9, 10, 14, 30), 0.0)]

        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = rows

        with patch(
            "app.routes.passivo_routes.get_db", return_value=iter([mock_session])
        ):
            resp = client.get(
                f"/cruzamento/car/{COD_IMOVEL}/passivos-ambientais?fonte=queimadas"
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["passivos"][0]["data_referencia"] == "2023-09-10"
