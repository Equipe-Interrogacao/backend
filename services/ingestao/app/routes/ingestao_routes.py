from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers import ingestao_controller
from app.schemas.propriedade_schema import PropriedadeBase, PropriedadeResponse

router = APIRouter(prefix="/ingestao", tags=["Ingestão"])


@router.get(
    "/propriedades",
    response_model=list[PropriedadeResponse],
    summary="Listar propriedades",
    description="Retorna todas as propriedades rurais cadastradas no banco.",
)
def listar(db: Session = Depends(get_db)):
    return ingestao_controller.listar_propriedades(db)


@router.get(
    "/propriedades/{cod_car}",
    response_model=PropriedadeResponse,
    summary="Buscar propriedade por CAR",
    description="Retorna os dados cadastrais de uma propriedade a partir do código CAR.",
    responses={404: {"description": "Propriedade não encontrada"}},
)
def buscar(cod_car: str, db: Session = Depends(get_db)):
    return ingestao_controller.buscar_propriedade(cod_car, db)


@router.post(
    "/propriedades",
    response_model=PropriedadeResponse,
    status_code=201,
    summary="Criar propriedade",
    description="Cadastra uma nova propriedade rural a partir dos dados fornecidos.",
)
def criar(payload: PropriedadeBase, db: Session = Depends(get_db)):
    return ingestao_controller.criar_propriedade(payload.model_dump(), db)
