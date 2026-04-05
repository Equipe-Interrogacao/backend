from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import imovel_controller
from app.schemas.imovel_schema import ImovelCarResponse

router = APIRouter(tags=["Imóvel CAR"])


@router.get(
    "/imovel",
    response_model=ImovelCarResponse,
    summary="Buscar imóvel por código CAR",
    description=(
        "Consulta a tabela `imovel` (Postgres + PostGIS) pelo código CAR. "
        "Retorna dados cadastrais para visualização."
    ),
    responses={
        400: {"description": "Formato de código CAR inválido"},
        404: {"description": "Imóvel não encontrado"},
        500: {"description": "Erro interno do servidor"},
    },
)
def get_imovel_por_car(
    car: str = Query(
        ...,
        min_length=1,
        description="Código CAR (estadual numérico ou federal)",
    ),
    db: Session = Depends(get_db),
):
    return imovel_controller.buscar_imovel_por_car(car, db)
