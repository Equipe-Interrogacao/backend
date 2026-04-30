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


async def buscar_stats_inpe_por_propriedade(cod_imovel: str) -> dict:
    """
    Retorna resumo de sobreposição INPE para a propriedade usando queries espaciais
    (ST_Intersection para PRODES, ST_Intersects para DETER, ST_DWithin para focos).
    """
    stats: dict = {"prodes_poligonos": 0, "prodes_area_ha": 0.0, "deter": 0, "focos": 0}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r_sob = await client.get(
                f"{GERENCIAMENTO_BANCO_URL}/banco/desmatamento-prodes/sobreposicao/{cod_imovel}"
            )
            if r_sob.status_code == 200:
                d = r_sob.json()
                stats["prodes_poligonos"] = d.get("n_poligonos", 0)
                stats["prodes_area_ha"] = d.get("area_ha", 0.0)

            r_deter = await client.get(
                f"{GERENCIAMENTO_BANCO_URL}/banco/alerta-deter/por-propriedade/{cod_imovel}"
            )
            if r_deter.status_code == 200:
                stats["deter"] = len(r_deter.json())

            r_focos = await client.get(
                f"{GERENCIAMENTO_BANCO_URL}/banco/foco-queimada/por-propriedade/{cod_imovel}",
            )
            if r_focos.status_code == 200:
                stats["focos"] = len(r_focos.json())

    except Exception as exc:
        logger.warning(f"Falha ao buscar stats INPE por propriedade ({cod_imovel}): {exc}")
    return stats
