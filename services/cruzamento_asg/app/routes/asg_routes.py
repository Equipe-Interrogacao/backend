from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers import asg_controller
from app.schemas.asg_schema import AnaliseASGBase, AnaliseASGResponse

router = APIRouter(prefix="/asg", tags=["Cruzamento ASG"])


@router.get(
    "/analises",
    response_model=list[AnaliseASGResponse],
    summary="Listar análises ASG",
    description="Retorna todas as análises ASG geradas para propriedades rurais.",
)
def listar(db: Session = Depends(get_db)):
    return asg_controller.listar_analises(db)


@router.get(
    "/analises/{cod_car}",
    response_model=AnaliseASGResponse,
    summary="Buscar análise ASG por CAR",
    description=(
        "Retorna os indicadores ASG de uma propriedade: desmatamento, déficit de APP, "
        "déficit de Reserva Legal e sobreposições com áreas protegidas."
    ),
    responses={404: {"description": "Análise ASG não encontrada para este CAR"}},
)
def buscar(cod_car: str, db: Session = Depends(get_db)):
    return asg_controller.buscar_analise(cod_car, db)


@router.post(
    "/analises",
    response_model=AnaliseASGResponse,
    status_code=201,
    summary="Criar análise ASG",
    description="Registra uma nova análise ASG para uma propriedade rural.",
)
def criar(payload: AnaliseASGBase, db: Session = Depends(get_db)):
    return asg_controller.criar_analise(payload.model_dump(), db)
