import logging

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.schemas.imovel_schema import ImovelCarResponse
from app.services.imovel_service import ImovelService
from app.utils.car_validator import FormatoCarInvalidoError

logger = logging.getLogger(__name__)
_service = ImovelService()


def buscar_imovel_por_car(codigo: str, db: Session) -> ImovelCarResponse:
    try:
        imovel = _service.buscar_por_car(db, codigo)
    except FormatoCarInvalidoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SQLAlchemyError:
        logger.exception("Erro ao consultar imóvel por CAR")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao consultar o banco de dados",
        ) from None

    if not imovel:
        raise HTTPException(
            status_code=404,
            detail="Imóvel não encontrado para o código CAR informado",
        )

    return ImovelCarResponse.model_validate(imovel)
