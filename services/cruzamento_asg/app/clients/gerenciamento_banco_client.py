import os
import logging
import httpx

logger = logging.getLogger(__name__)

GERENCIAMENTO_BANCO_URL = os.getenv(
    "GERENCIAMENTO_BANCO_URL",
    "http://controller-gerenciamento-banco:8000"
)


async def buscar_por_car(cod_imovel: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{GERENCIAMENTO_BANCO_URL}/banco/propriedades/car/{cod_imovel}"
            )
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as exc:
        logger.warning(f"Falha ao consultar gerenciamento_banco para {cod_imovel}: {exc}")
        return None


async def buscar_sobreposicao_prodes(cod_imovel: str) -> dict:
    """Área real de desmatamento DENTRO da propriedade via ST_Intersection."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{GERENCIAMENTO_BANCO_URL}/banco/desmatamento-prodes/sobreposicao/{cod_imovel}"
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning(f"Falha ao calcular sobreposição PRODES ({cod_imovel}): {exc}")
    return {"n_poligonos": 0, "area_ha": 0.0, "por_ano": []}


async def buscar_deter_por_propriedade(cod_imovel: str) -> list[dict]:
    """Alertas DETER que interceptam a geometria da propriedade."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{GERENCIAMENTO_BANCO_URL}/banco/alerta-deter/por-propriedade/{cod_imovel}"
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning(f"Falha ao buscar DETER por propriedade ({cod_imovel}): {exc}")
    return []


async def buscar_focos_por_propriedade(cod_imovel: str) -> list[dict]:
    """Focos de queimada DENTRO da propriedade via ST_Within."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{GERENCIAMENTO_BANCO_URL}/banco/foco-queimada/por-propriedade/{cod_imovel}",
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning(f"Falha ao buscar focos por propriedade ({cod_imovel}): {exc}")
    return []


async def buscar_areas_protegidas_por_propriedade(cod_imovel: str) -> dict:
    """UCs, TIs, Assentamentos e Quilombolas que interceptam a propriedade."""
    result = {"uc": [], "ti": [], "assentamento": [], "quilombola": []}
    endpoints = {
        "uc": "unidade-conservacao",
        "ti": "terra-indigena",
        "assentamento": "assentamento",
        "quilombola": "quilombola",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for chave, path in endpoints.items():
                resp = await client.get(
                    f"{GERENCIAMENTO_BANCO_URL}/banco/{path}/por-propriedade/{cod_imovel}"
                )
                if resp.status_code == 200:
                    result[chave] = resp.json()
    except Exception as exc:
        logger.warning(f"Falha ao buscar áreas protegidas por propriedade ({cod_imovel}): {exc}")
    return result
