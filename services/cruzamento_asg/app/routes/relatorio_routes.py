from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.controllers import relatorio_controller
from app.schemas.relatorio_asg_schema import RelatorioASGResponse

router = APIRouter(prefix="/relatorio", tags=["Relatório ASG"])


@router.get(
    "/car/{cod_imovel:path}/asg",
    response_model=RelatorioASGResponse,
    summary="Relatório ASG consolidado (JSON)",
    description=(
        "Agrega SICAR, cruzamentos INPE (PRODES, DETER, queimadas) e áreas protegidas "
        "(quando disponível). Cada seção traz rastreabilidade (fonte, data de referência). "
        "Imóvel inexistente: relatório vazio, HTTP 200."
    ),
)
async def relatorio_asg(cod_imovel: str) -> RelatorioASGResponse:
    return await relatorio_controller.get_relatorio_json(cod_imovel)


@router.get(
    "/car/{cod_imovel:path}/asg/export",
    summary="Exportar relatório (GeoPackage ou GeoJSON)",
    description="formato=gpkg: ficheiro .gpkg (QGIS). formato=geojson: FeatureCollection.",
    response_class=Response,
)
async def relatorio_asg_export(
    cod_imovel: str,
    formato: str = Query(
        "gpkg",
        description="gpkg — GeoPackage OGC; geojson — FeatureCollection (RFC 7946)",
    ),
) -> Response:
    f = formato.lower().strip()
    if f not in ("gpkg", "geojson"):
        raise HTTPException(
            status_code=422,
            detail="formato deve ser 'gpkg' ou 'geojson'",
        )
    return await relatorio_controller.exportar(cod_imovel, f)
