import logging
from typing import AsyncGenerator, Optional

import httpx

logger = logging.getLogger(__name__)

# GeoServer público do CAR — sem reCAPTCHA, sem autenticação
SICAR_WFS_URL = "https://geoserver.car.gov.br/geoserver/sicar/wfs"
PAGE_SIZE = 500
MAX_RETRIES = 3

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ASG-Ingestao/1.0)",
    "Accept": "application/json, */*",
}


def _layer_por_estado(estado: str) -> str:
    """Retorna o typeName da camada WFS para o estado informado."""
    return f"sicar:sicar_imoveis_{estado.lower()}"


async def _fetch_pagina(client: httpx.AsyncClient, params: dict) -> dict:
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(SICAR_WFS_URL, params=params, headers=_HEADERS)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            corpo = resp.text

            if not corpo.strip():
                logger.warning(f"Tentativa {tentativa}: resposta vazia (status={resp.status_code})")
                if tentativa == MAX_RETRIES:
                    return {}
                continue

            if "json" in content_type or corpo.strip().startswith("{"):
                return resp.json()

            logger.error(
                f"Resposta inesperada do servidor (content-type={content_type}):\n{corpo[:400]}"
            )
            return {}

        except httpx.HTTPStatusError as exc:
            logger.warning(
                f"Tentativa {tentativa}/{MAX_RETRIES} — HTTP {exc.response.status_code}: "
                f"{exc.response.text[:200]}"
            )
            if tentativa == MAX_RETRIES:
                raise
        except httpx.RequestError as exc:
            logger.warning(f"Tentativa {tentativa}/{MAX_RETRIES} — Erro de rede: {exc}")
            if tentativa == MAX_RETRIES:
                raise

    return {}


async def buscar_imovel_por_cod(cod_imovel: str) -> Optional[dict]:
    """
    Busca um único imóvel no SICAR pelo cod_imovel via CQL_FILTER.
    Extrai o estado do próprio código (ex: 'SP-...' → camada sicar_imoveis_sp).
    Retorna a feature GeoJSON ou None se não encontrado.
    """
    from typing import Optional  # noqa: F811

    uf = cod_imovel.split("-")[0].lower() if "-" in cod_imovel else "sp"
    type_name = _layer_por_estado(uf)

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "CQL_FILTER": f"cod_imovel='{cod_imovel}'",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info(f"SICAR — buscando imóvel avulso: {cod_imovel}")
        data = await _fetch_pagina(client, params)

    features = data.get("features", [])
    if not features:
        logger.info(f"Imóvel {cod_imovel} não encontrado no SICAR.")
        return None

    return features[0]


async def buscar_imoveis_por_estado(
    estado: str = "SP",
    page_size: int = PAGE_SIZE,
) -> AsyncGenerator[list[dict], None]:
    """
    Gera páginas de features GeoJSON do GeoServer público do CAR.

    Camada: sicar:sicar_imoveis_{uf}  (ex: sicar:sicar_imoveis_sp)
    Coordenadas: EPSG:4326 (WGS84) via srsName
    Paginação: startIndex + count (WFS 2.0)
    """
    type_name = _layer_por_estado(estado)

    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": page_size,
    }

    start_index = 0
    async with httpx.AsyncClient(timeout=120.0) as client:
        logger.info(
            f"Iniciando ingestão SICAR — estado={estado} "
            f"layer={type_name} URL={SICAR_WFS_URL}"
        )

        while True:
            params = {**params_base, "startIndex": start_index}
            logger.info(f"SICAR WFS — startIndex={start_index} count={page_size}")

            data = await _fetch_pagina(client, params)

            if not data:
                logger.warning("Nenhum dado retornado — encerrando paginação.")
                break

            features: list[dict] = data.get("features", [])
            total = data.get("totalFeatures") or data.get("numberMatched", "?")

            if not features:
                logger.info(f"Sem features (total={total}) — paginação encerrada.")
                break

            logger.info(f"Página recebida: {len(features)} features (total={total})")
            yield features

            if len(features) < page_size:
                logger.info(f"Última página ({len(features)} < {page_size}) — concluído.")
                break

            start_index += page_size
