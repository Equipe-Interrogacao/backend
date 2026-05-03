import re
from typing import Literal, Union

from fastapi.responses import JSONResponse, Response

from app.schemas.relatorio_asg_schema import RelatorioASGResponse
from app.services.relatorio_asg_service import montar_relatorio
from app.services.relatorio_export import montar_geojson, montar_gpkg

_FMT = Literal["gpkg", "geojson"]


def _nome_arquivo_seguro(cod_imovel: str, ext: str) -> str:
    safe = re.sub(r"[^\w\-.]+", "_", cod_imovel)[:120]
    return f"relatorio_asg_{safe}.{ext}"


async def get_relatorio_json(cod_imovel: str) -> RelatorioASGResponse:
    data, _ = await montar_relatorio(cod_imovel)
    return data


async def exportar(cod_imovel: str, formato: _FMT) -> Union[Response, JSONResponse]:
    _, d = await montar_relatorio(cod_imovel)
    if formato == "gpkg":
        buf = montar_gpkg(
            d.imovel, d.prodes_poligonos, d.deter, d.focos, d.ap
        )
        name = _nome_arquivo_seguro(cod_imovel, "gpkg")
        return Response(
            content=buf,
            media_type="application/vnd.sqlite3",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )
    coll = montar_geojson(
        d.imovel, d.prodes_poligonos, d.deter, d.focos, d.ap
    )
    return JSONResponse(
        content=coll,
        headers={
            "Content-Disposition": f'attachment; filename="{_nome_arquivo_seguro(cod_imovel, "geojson")}"',
        },
    )
