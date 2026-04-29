"""
Cliente HTTP assíncrono para UCs do ICMBio (Limites Oficiais — INDE).

WFS: https://geoservicos.inde.gov.br/geoserver/ICMBio/wfs
Layer: ICMBio:limiteucsfederais_a
Filtro por ufabrang contendo a sigla do estado.
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

ICMBIO_WFS_URL = os.getenv(
    "ICMBIO_WFS_URL",
    "https://geoservicos.inde.gov.br/geoserver/ICMBio/wfs",
)
ICMBIO_LAYER = os.getenv("ICMBIO_LAYER", "ICMBio:limiteucsfederais_a")
PAGE_SIZE = int(os.getenv("ICMBIO_PAGE_SIZE", "50"))
MAX_RETRIES = 3

# Bounding box de SP (minX, minY, maxX, maxY, CRS)
SP_BBOX = "-53.11,-25.31,-44.16,-19.78,EPSG:4326"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ASG-Ingestao/1.0)",
    "Accept": "application/json, */*",
}


async def _fetch_pagina(
    client: httpx.AsyncClient,
    params: dict,
    tentativa: int = 1,
) -> dict:
    try:
        resp = await client.get(ICMBIO_WFS_URL, params=params, headers=_HEADERS)
        resp.raise_for_status()
        if not resp.text.strip():
            logger.warning(f"[ICMBio] Resposta vazia (tentativa {tentativa})")
            return {}
        return resp.json()

    except json.JSONDecodeError:
        count_atual = int(params.get("count", PAGE_SIZE))
        novo_count = count_atual // 2
        if novo_count < 1:
            logger.error(f"[ICMBio] JSON truncado mesmo com count={count_atual}. Abortando.")
            return {}
        logger.warning(f"[ICMBio] JSON truncado — reduzindo count para {novo_count}.")
        return await _fetch_pagina(client, {**params, "count": novo_count}, tentativa + 1)

    except httpx.HTTPStatusError as exc:
        logger.warning(
            f"[ICMBio] Tentativa {tentativa}/{MAX_RETRIES} — "
            f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        )
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise

    except httpx.RequestError as exc:
        logger.warning(f"[ICMBio] Tentativa {tentativa}/{MAX_RETRIES} — Rede: {exc}")
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise


async def buscar_ucs_por_estado(
    uf: str = "SP",
    page_size: int = PAGE_SIZE,
) -> AsyncGenerator[list[dict], None]:
    """Gera páginas de features GeoJSON de UCs do ICMBio para o estado informado."""
    cql_filter = f"ufabrang LIKE '%{uf.upper()}%'"

    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": ICMBIO_LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": page_size,
        "CQL_FILTER": cql_filter,
        "format_options": "DECIMALS:5",  # reduz precisão → resposta menor
        "sortBy": "ogc_fid",             # paginação estável
    }

    start_index = 0
    current_page_size = page_size

    async with httpx.AsyncClient(timeout=300.0, verify=False) as client:
        logger.info(f"[ICMBio] Iniciando ingestão — uf={uf} layer={ICMBIO_LAYER}")

        while True:
            params = {**params_base, "startIndex": start_index, "count": current_page_size}
            logger.info(f"[ICMBio] WFS — startIndex={start_index} count={current_page_size}")

            data = await _fetch_pagina(client, params)
            if not data:
                logger.warning("[ICMBio] Sem dados — encerrando paginação.")
                break

            features: list[dict] = data.get("features", [])
            total = data.get("totalFeatures") or data.get("numberMatched", "?")

            if not features:
                logger.info(f"[ICMBio] Sem features (total={total}) — concluído.")
                break

            logger.info(f"[ICMBio] {len(features)} features (startIndex={start_index}, total={total})")
            yield features

            if len(features) < current_page_size:
                logger.info("[ICMBio] Última página — concluído.")
                break

            start_index += len(features)
