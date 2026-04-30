"""
Cliente HTTP assíncrono para BDQueimadas (INPE / TerraBrasilis).

Acessa o GeoServer WFS do BDQueimadas via camadas anuais:
  dados_abertos:focos_{ano}_br_satref

Filtro por estado='SÃO PAULO' (campo estado em caixa-alta por extenso).
Paginação: startIndex + count + sortBy=id_foco_bdq.
Retry: 3 tentativas com timeout de 120 s.
SSL: verify=False (certificado auto-assinado no servidor INPE).

Variáveis de ambiente (opcionais):
  QUEIMADAS_WFS_URL  — URL base do WFS (default: .../geoserver/wfs)
  QUEIMADAS_ANO      — Ano padrão quando não informado (default: 2024)
"""

import json
import logging
import os
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

QUEIMADAS_WFS_URL = os.getenv(
    "QUEIMADAS_WFS_URL",
    "https://terrabrasilis.dpi.inpe.br/queimadas/geoserver/wfs",
)
QUEIMADAS_ANO_DEFAULT = int(os.getenv("QUEIMADAS_ANO", "2024"))

# Mapeamento estado → nome completo usado na API (caixa-alta)
_ESTADO_NOME: dict[str, str] = {
    "SP": "SÃO PAULO",
    "MG": "MINAS GERAIS",
    "RJ": "RIO DE JANEIRO",
    "BA": "BAHIA",
    "PR": "PARANÁ",
    "RS": "RIO GRANDE DO SUL",
    "SC": "SANTA CATARINA",
    "GO": "GOIÁS",
    "MS": "MATO GROSSO DO SUL",
    "MT": "MATO GROSSO",
    "PA": "PARÁ",
    "AM": "AMAZONAS",
    "CE": "CEARÁ",
    "PE": "PERNAMBUCO",
    "MA": "MARANHÃO",
    "TO": "TOCANTINS",
    "RO": "RONDÔNIA",
    "AC": "ACRE",
    "AP": "AMAPÁ",
    "RR": "RORAIMA",
    "PI": "PIAUÍ",
    "AL": "ALAGOAS",
    "SE": "SERGIPE",
    "RN": "RIO GRANDE DO NORTE",
    "PB": "PARAÍBA",
    "ES": "ESPÍRITO SANTO",
    "DF": "DISTRITO FEDERAL",
}

PAGE_SIZE = int(os.getenv("QUEIMADAS_PAGE_SIZE", "200"))
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
        resp = await client.get(QUEIMADAS_WFS_URL, params=params, headers=_HEADERS)
        resp.raise_for_status()

        if not resp.text.strip():
            logger.warning(f"[Queimadas] Resposta vazia (tentativa {tentativa})")
            return {}

        return resp.json()

    except json.JSONDecodeError:
        count_atual = int(params.get("count", PAGE_SIZE))
        novo_count = count_atual // 2
        if novo_count < 5:
            logger.error(f"[Queimadas] JSON truncado mesmo com count={count_atual}. Abortando.")
            return {}
        logger.warning(
            f"[Queimadas] JSON truncado com count={count_atual} — "
            f"reduzindo para {novo_count}."
        )
        return await _fetch_pagina(client, {**params, "count": novo_count}, tentativa + 1)

    except httpx.HTTPStatusError as exc:
        # 400 normalmente significa layer inexistente no WFS (ano ainda não publicado)
        if exc.response.status_code == 400:
            layer = params.get("typeName", "?")
            logger.warning(
                f"[Queimadas] Layer '{layer}' não disponível no WFS (HTTP 400) — "
                "ano provavelmente ainda não publicado. Pulando."
            )
            return {}
        logger.warning(
            f"[Queimadas] Tentativa {tentativa}/{MAX_RETRIES} — "
            f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        )
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise

    except httpx.RequestError as exc:
        logger.warning(f"[Queimadas] Tentativa {tentativa}/{MAX_RETRIES} — Rede: {exc}")
        if tentativa < MAX_RETRIES:
            return await _fetch_pagina(client, params, tentativa + 1)
        raise

    return {}


async def buscar_focos_por_estado(
    estado: str = "SP",
    ano: int = QUEIMADAS_ANO_DEFAULT,
    page_size: int = PAGE_SIZE,
) -> AsyncGenerator[list[dict], None]:
    """
    Gera páginas de features GeoJSON de focos de incêndio do BDQueimadas (WFS).

    Parâmetros:
        estado    — Sigla do estado (ex.: 'SP').
        ano       — Ano de referência (ex.: 2024).
        page_size — Features por página (default: 200).

    Yields:
        Lista de dicts com os dados de cada foco de incêndio.
    """
    nome_estado = _ESTADO_NOME.get(estado.upper(), estado.upper())
    layer = f"dados_abertos:focos_{ano}_br_satref"
    cql_filter = f"estado='{nome_estado}'"

    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": layer,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "count": page_size,
        "CQL_FILTER": cql_filter,
        "sortBy": "id_foco_bdq",
    }

    start_index = 0
    current_page_size = page_size

    async with httpx.AsyncClient(timeout=120.0, verify=False, follow_redirects=True) as client:
        logger.info(
            f"[Queimadas] Iniciando ingestão — estado={estado} ({nome_estado}) "
            f"ano={ano} layer={layer}"
        )

        while True:
            params = {**params_base, "startIndex": start_index, "count": current_page_size}
            logger.info(f"[Queimadas] WFS — startIndex={start_index} count={current_page_size}")

            data = await _fetch_pagina(client, params)

            if not data:
                logger.warning("[Queimadas] Sem dados — encerrando paginação.")
                break

            features: list[dict] = data.get("features", [])
            total = data.get("totalFeatures") or data.get("numberMatched", "?")

            if not features:
                logger.info(f"[Queimadas] Sem features (total={total}) — concluído.")
                break

            logger.info(
                f"[Queimadas] {len(features)} features "
                f"(startIndex={start_index}, total={total})"
            )
            yield features

            if len(features) < current_page_size:
                logger.info("[Queimadas] Última página — concluído.")
                break

            start_index += len(features)
