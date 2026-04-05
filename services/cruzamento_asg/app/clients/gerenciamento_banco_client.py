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
