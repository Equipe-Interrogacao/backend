"""
Cliente HTTP assíncrono para Terras Indígenas da FUNAI.

WFS: https://geoserver.funai.gov.br/geoserver/Funai/ows
Layer: Funai:tis_poligonais
Filtro por uf_sigla contendo a sigla do estado.
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

FUNAI_WFS_URL = os.getenv(
    "FUNAI_WFS_URL",
    "https://geoserver.funai.gov.br/geoserver/Funai/ows",
)
FUNAI_LAYER = os.getenv("FUNAI_LAYER", "Funai:tis_poligonais")
PAGE_SIZE = int(os.getenv("FUNAI_PAGE_SIZE", "50"))
MAX_RETRIES = 3

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
        resp = await client.get(FUNAI_WFS_URL, params=params, headers=_HEADERS)
        resp.raise_for_status()
        if not resp.text.strip():
            logger.warning(f"[FUNAI] Resposta vazia (tentativa {tentativa})")
            return {}
        return resp.json()

    except json.JSONDecodeError:
        count_atual = int(params.get("count", PAGE_SIZE))
        novo_count = count_atual // 2
        if novo_count < 5:
            logger.error(f"[FUNAI] JSON truncado mesmo com count={count_atual}. Abortando.")
            return {}
        logger.warning(f"[FUNAI] JSON truncado — reduzindo count para {novo_count}.")
        return await _fetch_pagina(client, {**params, "count": novo_count}, tentativa + 1)

    except httpx.HTTPStatusError as exc:
        logger.warning(
            f"[FUNAI] Tentativa {tentativa}/{MAX_RETRIES} — "
            f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        )
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise

    except httpx.RequestError as exc:
        logger.warning(f"[FUNAI] Tentativa {tentativa}/{MAX_RETRIES} — Rede: {exc}")
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise


async def buscar_tis_por_estado(
    uf: str = "SP",
    page_size: int = PAGE_SIZE,
) -> AsyncGenerator[list[dict], None]:
    """Gera páginas de features GeoJSON de TIs da FUNAI para o estado informado."""
    cql_filter = f"uf_sigla LIKE '%{uf.upper()}%'"

    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": FUNAI_LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:4674",  # SIRGAS 2000 — único aceito pelo GeoServer FUNAI
        "count": page_size,
        "CQL_FILTER": cql_filter,
        "sortBy": "gid",
    }

    start_index = 0
    current_page_size = page_size

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        logger.info(f"[FUNAI] Iniciando ingestão — uf={uf} layer={FUNAI_LAYER}")

        while True:
            params = {**params_base, "startIndex": start_index, "count": current_page_size}
            logger.info(f"[FUNAI] WFS — startIndex={start_index} count={current_page_size}")

            data = await _fetch_pagina(client, params)
            if not data:
                logger.warning("[FUNAI] Sem dados — encerrando paginação.")
                break

            features: list[dict] = data.get("features", [])
            total = data.get("totalFeatures") or data.get("numberMatched", "?")

            if not features:
                logger.info(f"[FUNAI] Sem features (total={total}) — concluído.")
                break

            logger.info(f"[FUNAI] {len(features)} features (startIndex={start_index}, total={total})")
            yield features

            if len(features) < current_page_size:
                logger.info("[FUNAI] Última página — concluído.")
                break

            start_index += len(features)
