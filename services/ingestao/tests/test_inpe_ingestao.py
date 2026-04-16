"""
Testes de integração para os endpoints INPE (PRODES, DETER, BDQueimadas).

Cobertura:
  - POST /ingestao/inpe/{fonte}/ingerir → 202 Accepted
  - POST /ingestao/inpe/{fonte}/ingerir com ingestão já rodando → 409 Conflict
  - GET  /ingestao/inpe/{fonte}/status → campos obrigatórios
  - GET  /ingestao/inpe/{fonte}/status via rota genérica
  - GET  /ingestao/inpe/invalida/status → 404
  - Helpers internos: _converter_geometria, _extrair_dados_feature, _extrair_dados_foco
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.services import (
    inpe_prodes_ingestao_service as prodes_svc,
    inpe_deter_ingestao_service as deter_svc,
    inpe_queimadas_ingestao_service as queimadas_svc,
)
from app.services.inpe_prodes_ingestao_service import (
    _converter_geometria as prodes_conv,
    _extrair_dados_feature as prodes_extrair,
)
from app.services.inpe_deter_ingestao_service import (
    _converter_geometria as deter_conv,
    _extrair_dados_feature as deter_extrair,
)
from app.services.inpe_queimadas_ingestao_service import (
    _converter_geometria_ponto,
    _extrair_dados_foco,
)

# ---------------------------------------------------------------------------
# Fixtures de features GeoJSON sintéticas
# ---------------------------------------------------------------------------

_POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-47.0, -23.0],
            [-47.0, -22.5],
            [-46.5, -22.5],
            [-46.5, -23.0],
            [-47.0, -23.0],
        ]
    ],
}

_PRODES_FEATURE = {
    "id": "prodes_cerrado_nb.42",
    "type": "Feature",
    "geometry": _POLYGON_GEOJSON,
    "properties": {
        "year": 2023,
        "areakm": 1.5,
        "classname": "d",
        "state": "São Paulo",
        "municipali": "Campinas",
        "biome": "Cerrado",
    },
}

_DETER_FEATURE = {
    "id": "deter-cerrado.99",
    "type": "Feature",
    "geometry": _POLYGON_GEOJSON,
    "properties": {
        "classname": "DESMATAMENTO_CR",
        "view_date": "2024-03-15T00:00:00Z",
        "areamunkm": 0.8,
        "uc": None,
        "uf": "SP",
        "municipali": "Sorocaba",
        "biome": "Cerrado",
    },
}

_QUEIMADAS_FOCO = {
    "id": 12345,
    "lat": -22.9,
    "lon": -47.1,
    "data_hora_gmt": "2024-09-01T14:30:00Z",
    "satelite": "AQUA_M-T",
    "municipio": "Campinas",
    "estado": "SP",
    "pais": "Brasil",
    "bioma": "Cerrado",
    "frp": 15.3,
}


# ===========================================================================
# Testes unitários dos helpers de serviço
# ===========================================================================

class TestConverterGeometriaProdes:
    def test_polygon_vira_multipolygon(self):
        result = prodes_conv(_POLYGON_GEOJSON)
        assert result is not None

    def test_geometria_invalida_retorna_none(self):
        result = prodes_conv({"type": "Point", "coordinates": [0, 0]})
        # Point sem área → converte via convex_hull mas pode ser válido;
        # chave corrompida deve retornar None
        result_bad = prodes_conv({"type": "INVALIDO"})
        assert result_bad is None


class TestExtrairDadosFeatureProdes:
    def test_extrai_campos_basicos(self):
        dados = prodes_extrair(_PRODES_FEATURE, uf="SP")
        assert dados is not None
        assert dados["id_poligono"] == "prodes.prodes_cerrado_nb.42"
        assert dados["ano"] == 2023
        assert dados["area_km2"] == 1.5
        assert dados["uf"] == "SP"
        assert dados["municipio"] == "Campinas"
        assert dados["bioma"] == "Cerrado"
        assert dados["geometria"] is not None

    def test_sem_geometria_retorna_none(self):
        feature = {**_PRODES_FEATURE, "geometry": None}
        assert prodes_extrair(feature) is None

    def test_sem_id_retorna_none(self):
        feature = {**_PRODES_FEATURE, "id": None, "properties": {}}
        assert prodes_extrair(feature) is None


class TestExtrairDadosFeatureDeter:
    def test_extrai_campos_basicos(self):
        dados = deter_extrair(_DETER_FEATURE, uf="SP")
        assert dados is not None
        assert dados["id_alerta"] == "deter.deter-cerrado.99"
        assert dados["classname"] == "DESMATAMENTO_CR"
        assert dados["uf"] == "SP"
        assert dados["municipio"] == "Sorocaba"
        assert dados["geometria"] is not None

    def test_descarta_uf_diferente(self):
        feature = {
            **_DETER_FEATURE,
            "properties": {**_DETER_FEATURE["properties"], "uf": "MG"},
        }
        assert deter_extrair(feature, uf="SP") is None

    def test_sem_geometria_retorna_none(self):
        feature = {**_DETER_FEATURE, "geometry": None}
        assert deter_extrair(feature) is None


class TestExtracaoFocoQueimada:
    def test_extrai_campos_basicos(self):
        dados = _extrair_dados_foco(_QUEIMADAS_FOCO, estado="SP")
        assert dados is not None
        assert dados["id_foco"] == "queimadas.12345"
        assert dados["latitude"] == -22.9
        assert dados["longitude"] == -47.1
        assert dados["satelite"] == "AQUA_M-T"
        assert dados["estado"] == "SP"
        assert dados["frp"] == 15.3
        assert dados["geometria"] is not None

    def test_descarta_estado_diferente(self):
        foco = {**_QUEIMADAS_FOCO, "estado": "MG"}
        assert _extrair_dados_foco(foco, estado="SP") is None

    def test_sem_id_retorna_none(self):
        foco = {**_QUEIMADAS_FOCO, "id": None}
        assert _extrair_dados_foco(foco) is None

    def test_sem_coordenadas_retorna_none(self):
        foco = {**_QUEIMADAS_FOCO, "lat": None, "lon": None}
        assert _extrair_dados_foco(foco) is None

    def test_converter_geometria_ponto_valido(self):
        geom = _converter_geometria_ponto(-22.9, -47.1)
        assert geom is not None

    def test_converter_geometria_ponto_nulo(self):
        assert _converter_geometria_ponto(None, -47.1) is None
        assert _converter_geometria_ponto(-22.9, None) is None


# ===========================================================================
# Testes de endpoint via TestClient
# ===========================================================================

class TestEndpointsProdes:
    def test_ingerir_retorna_202(self, client):
        with patch.object(prodes_svc, "_status", {**prodes_svc._status, "rodando": False}):
            resp = client.post("/ingestao/inpe/prodes/ingerir?estado=SP")
        assert resp.status_code == 202
        assert "mensagem" in resp.json()

    def test_ingerir_conflict_quando_ja_rodando(self, client):
        with patch.object(prodes_svc, "_status", {**prodes_svc._status, "rodando": True, "estado": "SP"}):
            resp = client.post("/ingestao/inpe/prodes/ingerir?estado=SP")
        assert resp.status_code == 409

    def test_status_retorna_campos_obrigatorios(self, client):
        resp = client.get("/ingestao/inpe/prodes/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "rodando" in body
        assert "total_salvos" in body
        assert "total_ignorados" in body


class TestEndpointsDeter:
    def test_ingerir_retorna_202(self, client):
        with patch.object(deter_svc, "_status", {**deter_svc._status, "rodando": False}):
            resp = client.post("/ingestao/inpe/deter/ingerir?estado=SP")
        assert resp.status_code == 202

    def test_ingerir_conflict_quando_ja_rodando(self, client):
        with patch.object(deter_svc, "_status", {**deter_svc._status, "rodando": True, "estado": "SP"}):
            resp = client.post("/ingestao/inpe/deter/ingerir?estado=SP")
        assert resp.status_code == 409

    def test_status_retorna_campos_obrigatorios(self, client):
        resp = client.get("/ingestao/inpe/deter/status")
        assert resp.status_code == 200
        assert "rodando" in resp.json()


class TestEndpointsQueimadas:
    def test_ingerir_retorna_202(self, client):
        with patch.object(queimadas_svc, "_status", {**queimadas_svc._status, "rodando": False}):
            resp = client.post("/ingestao/inpe/queimadas/ingerir?estado=SP&ano=2024")
        assert resp.status_code == 202

    def test_ingerir_conflict_quando_ja_rodando(self, client):
        with patch.object(queimadas_svc, "_status", {**queimadas_svc._status, "rodando": True, "estado": "SP"}):
            resp = client.post("/ingestao/inpe/queimadas/ingerir?estado=SP&ano=2024")
        assert resp.status_code == 409

    def test_status_retorna_campos_obrigatorios(self, client):
        resp = client.get("/ingestao/inpe/queimadas/status")
        assert resp.status_code == 200
        assert "rodando" in resp.json()


class TestRotaGenerica:
    def test_status_prodes_via_rota_generica(self, client):
        resp = client.get("/ingestao/inpe/prodes/status")
        assert resp.status_code == 200

    def test_fonte_invalida_retorna_404(self, client):
        resp = client.get("/ingestao/inpe/invalida/status")
        assert resp.status_code == 404
        assert "invalida" in resp.json()["detail"]
