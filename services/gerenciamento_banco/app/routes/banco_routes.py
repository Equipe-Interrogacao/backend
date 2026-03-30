from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers import banco_controller
from app.schemas.propriedade_schema import PropriedadeCreate, PropriedadeResponse

router = APIRouter(prefix="/banco", tags=["Gerenciamento do Banco"])


@router.get(
    "/propriedades",
    response_model=list[PropriedadeResponse],
    summary="Listar propriedades",
    description="Retorna todas as propriedades rurais armazenadas no banco.",
)
def listar(db: Session = Depends(get_db)):
    return banco_controller.listar_propriedades(db)


@router.get(
    "/propriedades/{id}",
    response_model=PropriedadeResponse,
    summary="Buscar propriedade por ID",
    description="Retorna os dados de uma propriedade a partir do seu ID interno.",
    responses={404: {"description": "Propriedade não encontrada"}},
)
def buscar(id: int, db: Session = Depends(get_db)):
    return banco_controller.buscar_propriedade(id, db)


@router.post(
    "/propriedades",
    response_model=PropriedadeResponse,
    status_code=201,
    summary="Criar propriedade",
    description="Insere uma nova propriedade rural no banco de dados, incluindo dados geoespaciais.",
)
def criar(payload: PropriedadeCreate, db: Session = Depends(get_db)):
    return banco_controller.criar_propriedade(payload.model_dump(), db)


@router.delete(
    "/propriedades/{id}",
    summary="Deletar propriedade",
    description="Remove uma propriedade rural do banco de dados pelo ID.",
    responses={404: {"description": "Propriedade não encontrada"}},
)
def deletar(id: int, db: Session = Depends(get_db)):
    return banco_controller.deletar_propriedade(id, db)
