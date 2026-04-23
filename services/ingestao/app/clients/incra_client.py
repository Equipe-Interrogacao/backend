"""
Cliente HTTP assíncrono para Projetos de Assentamento do INCRA.

WFS: https://panorama.sipam.gov.br/geoserver/ows
Layer: painel_do_fogo:assentamento_federal
Filtro por uf='SP'.
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

INCRA_WFS_URL = os.getenv(
    "INCRA_WFS_URL",
    "https://panorama.sipam.gov.br/geoserver/ows",
)
INCRA_LAYER = os.getenv("INCRA_LAYER", "painel_do_fogo:assentamento_federal")
PAGE_SIZE = int(os.getenv("INCRA_PAGE_SIZE", "50"))
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
        resp = await client.get(INCRA_WFS_URL, params=params, headers=_HEADERS)
        resp.raise_for_status()
        if not resp.text.strip():
            logger.warning(f"[INCRA] Resposta vazia (tentativa {tentativa})")
            return {}
        return resp.json()

    except json.JSONDecodeError:
        count_atual = int(params.get("count", PAGE_SIZE))
        novo_count = count_atual // 2
        if novo_count < 5:
            logger.error(f"[INCRA] JSON truncado mesmo com count={count_atual}. Abortando.")
            return {}
        logger.warning(f"[INCRA] JSON truncado — reduzindo count para {novo_count}.")
        return await _fetch_pagina(client, {**params, "count": novo_count}, tentativa + 1)

    except httpx.HTTPStatusError as exc:
        logger.warning(
            f"[INCRA] Tentativa {tentativa}/{MAX_RETRIES} — "
            f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        )
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise

    except httpx.RequestError as exc:
        logger.warning(f"[INCRA] Tentativa {tentativa}/{MAX_RETRIES} — Rede: {exc}")
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise


async def buscar_assentamentos_por_estado(
    uf: str = "SP",
    page_size: int = PAGE_SIZE,
) -> AsyncGenerator[list[dict], None]:
    """Gera páginas de features GeoJSON de assentamentos INCRA para o estado informado."""
    cql_filter = f"uf='{uf.upper()}'"

    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": INCRA_LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": page_size,
        "CQL_FILTER": cql_filter,
        "sortBy": "cd_sipra",
    }

    start_index = 0
    current_page_size = page_size

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        logger.info(f"[INCRA] Iniciando ingestão — uf={uf} layer={INCRA_LAYER}")

        while True:
            params = {**params_base, "startIndex": start_index, "count": current_page_size}
            logger.info(f"[INCRA] WFS — startIndex={start_index} count={current_page_size}")

            data = await _fetch_pagina(client, params)
            if not data:
                logger.warning("[INCRA] Sem dados — encerrando paginação.")
                break

            features: list[dict] = data.get("features", [])
            total = data.get("totalFeatures") or data.get("numberMatched", "?")

            if not features:
                logger.info(f"[INCRA] Sem features (total={total}) — concluído.")
                break

            logger.info(f"[INCRA] {len(features)} features (startIndex={start_index}, total={total})")
            yield features

            if len(features) < current_page_size:
                logger.info("[INCRA] Última página — concluído.")
                break

            start_index += len(features)
