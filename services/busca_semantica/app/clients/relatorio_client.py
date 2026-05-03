import os
import logging
import httpx

logger = logging.getLogger(__name__)

# O relatório ASG fica no mesmo serviço que o cruzamento, não num serviço separado
RELATORIO_ASG_URL = os.getenv("RELATORIO_ASG_URL", "http://controller-cruzamento-asg:8000")


async def obter_relatorio_car(car_id: str) -> dict | None:
    try:
        url = f"{RELATORIO_ASG_URL}/relatorio/car/{car_id}/asg"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"Relatorio ASG retornou {resp.status_code} para {url}")
            return {"status_code": resp.status_code, "text": resp.text}
    except Exception as exc:
        logger.exception(f"Erro ao chamar relatorio_asg {car_id}: {exc}")
        return None
