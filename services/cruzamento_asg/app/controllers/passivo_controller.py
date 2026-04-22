from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.clients.ingestao_client import buscar_geometria_propriedade
from app.schemas.passivo_ambiental_schema import (
    FonteINPE,
    PassivoAmbientalResponse,
)
from app.services.passivo_ambiental_service import cruzar_com_inpe

_TODAS_FONTES = [FonteINPE.deter, FonteINPE.prodes, FonteINPE.queimadas]


async def buscar_passivos_ambientais(
    cod_imovel: str,
    db: Session,
    fontes: Optional[list[FonteINPE]] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
) -> PassivoAmbientalResponse:
    geometria = await buscar_geometria_propriedade(cod_imovel)
    if geometria is None:
        raise HTTPException(
            status_code=404,
            detail=f"Propriedade '{cod_imovel}' nao encontrada. Verifique o codigo CAR ou ingira os dados primeiro.",
        )

    fontes_consulta = fontes if fontes else _TODAS_FONTES

    passivos = cruzar_com_inpe(
        db=db,
        geometria_geojson=geometria,
        fontes=fontes_consulta,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    area_total = round(sum(p.area_ha for p in passivos), 4)

    return PassivoAmbientalResponse(
        cod_imovel=cod_imovel,
        total_alertas=len(passivos),
        area_total_passivos_ha=area_total,
        passivos=passivos,
    )
