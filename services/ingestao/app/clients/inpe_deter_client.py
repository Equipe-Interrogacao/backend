"""
Cliente HTTP assíncrono para o DETER (TerraBrasilis / INPE).

GeoServer único: https://terrabrasilis.dpi.inpe.br/geoserver/wfs
Workspace relevante para SP: deter-cerrado-nb → layer deter_cerrado
Filtro por uf='SP' (sigla, 2 letras, maiúsculo).
SSL: verify=False (certificado auto-assinado no servidor INPE).
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

DETER_WFS_URL = os.getenv(
    "DETER_WFS_URL",
    "https://terrabrasilis.dpi.inpe.br/geoserver/wfs",
)
DETER_LAYER = os.getenv("DETER_LAYER", "deter-cerrado-nb:deter_cerrado")
DETER_UF_FIELD = os.getenv("DETER_UF_FIELD", "uf")

PAGE_SIZE = int(os.getenv("DETER_PAGE_SIZE", "50"))
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
        resp = await client.get(DETER_WFS_URL, params=params, headers=_HEADERS)
        resp.raise_for_status()

        if not resp.text.strip():
            logger.warning(f"[DETER] Resposta vazia (tentativa {tentativa})")
            return {}

        return resp.json()

    except json.JSONDecodeError:
        count_atual = int(params.get("count", PAGE_SIZE))
        novo_count = count_atual // 2
        if novo_count < 5:
            logger.error(f"[DETER] JSON truncado mesmo com count={count_atual}. Abortando.")
            return {}
        logger.warning(
            f"[DETER] JSON truncado com count={count_atual} — "
            f"reduzindo para {novo_count}."
        )
        return await _fetch_pagina(client, {**params, "count": novo_count}, tentativa + 1)

    except httpx.HTTPStatusError as exc:
        logger.warning(
            f"[DETER] Tentativa {tentativa}/{MAX_RETRIES} — "
            f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        )
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise

    except httpx.RequestError as exc:
        logger.warning(f"[DETER] Tentativa {tentativa}/{MAX_RETRIES} — Rede: {exc}")
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise

    return {}


async def buscar_alertas_por_estado(
    estado: str = "SP",
    page_size: int = PAGE_SIZE,
) -> AsyncGenerator[list[dict], None]:
    """
    Gera páginas de features GeoJSON do DETER (TerraBrasilis WFS).

    Parâmetros:
        estado    — Sigla do estado maiúscula (ex.: 'SP').
        page_size — Features por página (default: 500).
    """
    cql_filter = f"{DETER_UF_FIELD}='{estado.upper()}'"

    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": DETER_LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": page_size,
        "CQL_FILTER": cql_filter,
    }

    start_index = 0
    current_page_size = page_size

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        logger.info(
            f"[DETER] Iniciando ingestão — estado={estado} "
            f"layer={DETER_LAYER} filtro='{cql_filter}'"
        )

        while True:
            params = {**params_base, "startIndex": start_index, "count": current_page_size}
            logger.info(f"[DETER] WFS — startIndex={start_index} count={current_page_size}")

            data = await _fetch_pagina(client, params)

            if not data:
                logger.warning("[DETER] Sem dados — encerrando paginação.")
                break

            features: list[dict] = data.get("features", [])
            total = data.get("totalFeatures") or data.get("numberMatched", "?")

            if not features:
                logger.info(f"[DETER] Sem features (total={total}) — concluído.")
                break

            logger.info(f"[DETER] {len(features)} features (startIndex={start_index}, total={total})")
            yield features

            if len(features) < current_page_size:
                logger.info("[DETER] Última página — concluído.")
                break

            start_index += len(features)
