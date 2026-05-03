import os
import logging
import httpx

logger = logging.getLogger(__name__)

CRUZAMENTO_ASG_URL = os.getenv("CRUZAMENTO_ASG_URL", "http://controller-cruzamento-asg:8000")


async def chamar_cruzamento(path: str, params: dict | None = None) -> dict | None:
    try:
        url = f"{CRUZAMENTO_ASG_URL}{path}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"Cruzamento retornou {resp.status_code} para {url}")
            return {"status_code": resp.status_code, "text": resp.text}
    except Exception as exc:
        logger.exception(f"Erro ao chamar cruzamento_asg {path}: {exc}")
        return None
