from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers import busca_controller
from app.schemas.consulta_schema import ConsultaCreate, ConsultaResponse

router = APIRouter(prefix="/busca", tags=["Busca Semântica"])


@router.post(
    "/consulta",
    response_model=ConsultaResponse,
    status_code=201,
    summary="Realizar consulta em linguagem natural",
    description=(
        "Recebe uma pergunta em linguagem natural sobre uma propriedade rural "
        "(ex.: 'Houve desmatamento recente?' ou 'Existe passivo ambiental?') "
        "e retorna uma resposta com fontes rastreáveis."
    ),
)
async def consultar(payload: ConsultaCreate, db: Session = Depends(get_db)):
    return await busca_controller.realizar_consulta(payload, db)


@router.get(
    "/consultas",
    response_model=list[ConsultaResponse],
    summary="Listar consultas realizadas",
    description="Retorna o histórico de todas as consultas em linguagem natural já realizadas.",
)
def listar(db: Session = Depends(get_db)):
    return busca_controller.listar_consultas(db)


@router.get(
    "/intencoes",
    summary="Listar intenções suportadas",
    description="Retorna as intenções que o módulo de PLN reconhece e exemplos de palavras-chave.",
)
def listar_intencoes():
    from app.services.nlp_service import obter_intencoes_documentacao

    return obter_intencoes_documentacao()
