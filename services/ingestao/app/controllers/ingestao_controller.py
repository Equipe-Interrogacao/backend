from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.services.ingestao_service import IngestaoService
from app.services import sicar_ingestao_service

service = IngestaoService()


async def buscar_propriedade(cod_imovel: str, db: Session):
    """
    Busca no banco local. Se ausente, consulta o SICAR, persiste e retorna.
    Retorna 404 apenas se não encontrado em nenhuma fonte.
    """
    propriedade = await service.buscar_ou_ingerir_por_cod(db, cod_imovel)
    if not propriedade:
        raise HTTPException(
            status_code=404,
            detail=f"Imóvel '{cod_imovel}' não encontrado no banco nem no SICAR.",
        )
    return propriedade


def listar_propriedades(db: Session, limit: int = 100, offset: int = 0):
    return service.listar_propriedades(db, limit=limit, offset=offset)


def upsert_propriedade(dados: dict, db: Session):
    return service.upsert_propriedade(db, dados)


def iniciar_ingestao_sicar(estado: str, background_tasks: BackgroundTasks):
    status = sicar_ingestao_service.get_status()
    if status["rodando"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestão já está em execução para o estado '{status['estado']}'.",
        )
    background_tasks.add_task(sicar_ingestao_service.ingerir_estado, estado)
    return {
        "mensagem": f"Ingestão do estado '{estado}' iniciada em background.",
        "dica": "Consulte GET /ingestao/sicar/status para acompanhar o progresso.",
    }


def status_ingestao():
    return sicar_ingestao_service.get_status()
