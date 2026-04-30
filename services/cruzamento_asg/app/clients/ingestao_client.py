import os
import logging
import httpx

logger = logging.getLogger(__name__)

INGESTAO_URL = os.getenv(
    "INGESTAO_URL",
    "http://controller-ingestao:8000",
)


async def buscar_geometria_propriedade(cod_imovel: str) -> dict | None:
    """Retorna o GeoJSON da geometria da propriedade, ou None se nao encontrada."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{INGESTAO_URL}/ingestao/propriedades/{cod_imovel}"
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("geometria")
            return None
    except Exception as exc:
        logger.warning(f"Falha ao consultar ingestao para {cod_imovel}: {exc}")
        return None
