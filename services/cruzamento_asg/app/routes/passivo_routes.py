from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import passivo_controller
from app.schemas.passivo_ambiental_schema import (
    FonteINPE,
    PassivoAmbientalResponse,
)

router = APIRouter(prefix="/cruzamento", tags=["Passivos Ambientais"])


def _parse_fontes(fonte: Optional[str]) -> Optional[list[FonteINPE]]:
    if not fonte:
        return None
    valores = [v.strip().lower() for v in fonte.split(",") if v.strip()]
    parsed = []
    for v in valores:
        try:
            parsed.append(FonteINPE(v))
        except ValueError:
            continue
    return parsed or None


@router.get(
    "/car/{cod_imovel:path}/passivos-ambientais",
    response_model=PassivoAmbientalResponse,
    summary="Cruzar CAR com alertas INPE",
    description=(
        "Cruza o poligono da propriedade (CAR) com alertas do INPE "
        "(DETER, PRODES, queimadas) para identificar passivos ambientais. "
        "Retorna fonte, tipo de alerta, data de referencia e area de "
        "intersecao em hectares."
    ),
    responses={
        200: {"description": "Lista de passivos ambientais (pode ser vazia)"},
        404: {"description": "Propriedade nao encontrada para o codigo CAR informado"},
    },
)
async def passivos_ambientais(
    cod_imovel: str,
    fonte: Optional[str] = Query(
        None,
        description="Fontes INPE separadas por virgula: deter, prodes, queimadas. Sem filtro = todas.",
        examples=["deter,prodes"],
    ),
    data_inicio: Optional[date] = Query(
        None,
        description="Data inicial do filtro temporal (YYYY-MM-DD).",
    ),
    data_fim: Optional[date] = Query(
        None,
        description="Data final do filtro temporal (YYYY-MM-DD).",
    ),
    db: Session = Depends(get_db),
):
    fontes = _parse_fontes(fonte)
    return await passivo_controller.buscar_passivos_ambientais(
        cod_imovel=cod_imovel,
        db=db,
        fontes=fontes,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
