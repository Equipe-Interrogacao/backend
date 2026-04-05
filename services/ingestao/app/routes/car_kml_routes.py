"""Endpoints do MVP KML/CAR (memória), migrados de /app."""

from fastapi import APIRouter, HTTPException

from app.schemas.car_kml_schema import PropriedadeKmlOut
from app.services.car_kml_store import buscar_kml, listar_kml, total_kml

router = APIRouter(prefix="/ingestao/car-kml", tags=["Ingestão — CAR KML (MVP)"])


@router.get(
    "/propriedades",
    response_model=list[PropriedadeKmlOut],
    summary="Listar propriedades (KML em memória)",
    description=(
        "Dados lidos do ficheiro `data/car_propriedades.kml` na subida do serviço. "
        "Não consulta o PostgreSQL. Requer internet se o KML for apenas NetworkLink."
    ),
)
def listar_propriedades_kml():
    return listar_kml()


@router.get(
    "/propriedades/{cod_car}",
    response_model=PropriedadeKmlOut,
    summary="Buscar propriedade por CAR (KML em memória)",
    responses={404: {"description": "Propriedade não encontrada no cache KML"}},
)
def buscar_propriedade_kml(cod_car: str):
    item = buscar_kml(cod_car)
    if not item:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada no cache KML")
    return item


@router.get(
    "/health",
    summary="Estado do cache KML",
)
def health_kml():
    return {
        "fonte": "car_propriedades.kml",
        "total_propriedades": total_kml(),
    }
