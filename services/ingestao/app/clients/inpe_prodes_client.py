"""
Cliente HTTP assíncrono para o PRODES (TerraBrasilis / INPE).

GeoServer único: https://terrabrasilis.dpi.inpe.br/geoserver/wfs
Workspaces relevantes para SP:
  prodes-cerrado-nb      → layer yearly_deforestation
  prodes-mata-atlantica-nb → layer yearly_deforestation

Filtro por state='SÃO PAULO' (uppercase, nome completo).
SSL: verify=False (certificado auto-assinado no servidor INPE).

PAGE_SIZE pequeno (50) evita truncamento de JSON em respostas grandes com geometria.
Em caso de JSONDecodeError a página é reduzida pela metade e refeita.
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

PRODES_WFS_URL = os.getenv(
    "PRODES_WFS_URL",
    "https://terrabrasilis.dpi.inpe.br/geoserver/wfs",
)
PRODES_LAYER = os.getenv("PRODES_LAYER", "prodes-cerrado-nb:yearly_deforestation")
PRODES_STATE_FIELD = os.getenv("PRODES_STATE_FIELD", "state")

# Pequeno para evitar truncamento de JSON (geometrias são grandes)
PAGE_SIZE = int(os.getenv("PRODES_PAGE_SIZE", "50"))
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
    """
    Busca uma página WFS. Se o JSON vier truncado reduz o 'count' pela metade
    e tenta novamente (até o mínimo de 5 features por requisição).
    """
    try:
        resp = await client.get(PRODES_WFS_URL, params=params, headers=_HEADERS)
        resp.raise_for_status()

        corpo = resp.text
        if not corpo.strip():
            logger.warning(f"[PRODES] Resposta vazia (tentativa {tentativa})")
            return {}

        return resp.json()

    except json.JSONDecodeError:
        count_atual = int(params.get("count", PAGE_SIZE))
        novo_count = count_atual // 2
        if novo_count < 5:
            logger.error(
                f"[PRODES] JSON truncado mesmo com count={count_atual}. "
                "Abortando esta página."
            )
            return {}
        logger.warning(
            f"[PRODES] JSON truncado com count={count_atual} — "
            f"reduzindo para {novo_count} e tentando novamente."
        )
        return await _fetch_pagina(client, {**params, "count": novo_count}, tentativa + 1)

    except httpx.HTTPStatusError as exc:
        if tentativa <= MAX_RETRIES:
            logger.warning(
                f"[PRODES] Tentativa {tentativa}/{MAX_RETRIES} — "
                f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            )
            if tentativa < MAX_RETRIES:
                return await _fetch_pagina(client, params, tentativa + 1)
        raise

    except httpx.RequestError as exc:
        if tentativa <= MAX_RETRIES:
            logger.warning(
                f"[PRODES] Tentativa {tentativa}/{MAX_RETRIES} — Erro de rede: {exc}"
            )
            if tentativa < MAX_RETRIES:
                return await _fetch_pagina(client, params, tentativa + 1)
        raise

    return {}


async def buscar_desmatamento_por_estado(
    estado: str = "SP",
    nome_estado: str = "SÃO PAULO",
    page_size: int = PAGE_SIZE,
) -> AsyncGenerator[list[dict], None]:
    """
    Gera páginas de features GeoJSON do PRODES (TerraBrasilis WFS).

    Parâmetros:
        estado      — Sigla do estado (usada no log).
        nome_estado — Nome em caixa-alta para o CQL_FILTER (ex.: 'SÃO PAULO').
        page_size   — Features por página (default: 50 para evitar truncamento).
    """
    cql_filter = f"{PRODES_STATE_FIELD}='{nome_estado}'"

    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": PRODES_LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": page_size,
        "CQL_FILTER": cql_filter,
    }

    start_index = 0
    current_page_size = page_size

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        logger.info(
            f"[PRODES] Iniciando ingestão — estado={estado} "
            f"layer={PRODES_LAYER} page_size={page_size}"
        )

        while True:
            params = {**params_base, "startIndex": start_index, "count": current_page_size}
            logger.info(
                f"[PRODES] WFS — startIndex={start_index} count={current_page_size}"
            )

            data = await _fetch_pagina(client, params)

            if not data:
                logger.warning("[PRODES] Sem dados — encerrando paginação.")
                break

            features: list[dict] = data.get("features", [])
            total = data.get("totalFeatures") or data.get("numberMatched", "?")

            if not features:
                logger.info(f"[PRODES] Sem features (total={total}) — concluído.")
                break

            logger.info(
                f"[PRODES] {len(features)} features recebidas "
                f"(startIndex={start_index}, total={total})"
            )
            yield features

            if len(features) < current_page_size:
                logger.info("[PRODES] Última página — concluído.")
                break

            start_index += len(features)
