from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import ingestao_controller
from app.schemas.propriedade_schema import (
    PropriedadeBase,
    PropriedadeResponse,
    IngestaoStatusResponse,
)

router = APIRouter(prefix="/ingestao", tags=["Ingestão"])


# --------------------------------------------------------------------------- #
# Consulta de propriedades já ingeridas
# --------------------------------------------------------------------------- #

@router.get(
    "/propriedades",
    response_model=list[PropriedadeResponse],
    summary="Listar propriedades",
    description="Retorna propriedades rurais cadastradas no banco com paginação.",
)
def listar(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return ingestao_controller.listar_propriedades(db, limit=limit, offset=offset)


@router.get(
    "/propriedades/{cod_imovel:path}",
    response_model=PropriedadeResponse,
    summary="Buscar propriedade por código CAR",
    description="Retorna dados de uma propriedade pelo código CAR (cod_imovel).",
    responses={404: {"description": "Propriedade não encontrada"}},
)
async def buscar(cod_imovel: str, db: Session = Depends(get_db)):
    return await ingestao_controller.buscar_propriedade(cod_imovel, db)


@router.post(
    "/propriedades",
    response_model=PropriedadeResponse,
    status_code=201,
    summary="Upsert de propriedade",
    description="Insere ou atualiza uma propriedade pelo código CAR.",
)
def upsert(payload: PropriedadeBase, db: Session = Depends(get_db)):
    return ingestao_controller.upsert_propriedade(payload.model_dump(), db)


# --------------------------------------------------------------------------- #
# Ingestão SICAR via WFS
# --------------------------------------------------------------------------- #

@router.post(
    "/sicar/ingerir",
    status_code=202,
    summary="Iniciar ingestão SICAR",
    description=(
        "Dispara a ingestão em background de todos os imóveis rurais de um estado "
        "a partir da API WFS pública do SICAR (consulta.car.gov.br). "
        "O processo é idempotente — re-execuções atualizam registros existentes."
    ),
)
def iniciar_ingestao(
    estado: str = Query("SP", description="Sigla do estado (ex: SP, MG, RJ)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    return ingestao_controller.iniciar_ingestao_sicar(estado, background_tasks)


@router.get(
    "/sicar/status",
    response_model=IngestaoStatusResponse,
    summary="Status da ingestão SICAR",
    description="Retorna o progresso atual (ou último resultado) da ingestão SICAR.",
)
def status_ingestao():
    return ingestao_controller.status_ingestao()
