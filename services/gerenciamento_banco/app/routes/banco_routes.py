from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.controllers import banco_controller
from app.schemas.propriedade_schema import PropriedadeCreate, PropriedadeResponse

router = APIRouter(prefix="/banco", tags=["Gerenciamento do Banco"])

@router.get(
    "/imovel/{cod_imovel:path}/geometria",
    summary="Obter geometria GeoJSON (SCRUM-4)",
    responses={
        404: {"description": "CAR não encontrado"},
        500: {"description": "Erro interno no processamento geoespacial"}
    }
)
def obter_geometria(cod_imovel: str, db: Session = Depends(get_db)):
    try:
        return banco_controller.obter_geometria_geojson(cod_imovel, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get(
    "/propriedades",
    response_model=list[PropriedadeResponse],
    summary="Listar propriedades",
    description="Retorna propriedades com filtros opcionais por UF, município e status.",
)
def listar(
    uf: Optional[str] = Query(None, description="Sigla do estado (ex: SP)"),
    municipio: Optional[str] = Query(None, description="Nome parcial do município"),
    status_imovel: Optional[str] = Query(None, description="Status: AT, PE, CA, SU"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return banco_controller.listar_propriedades(
        db, uf, municipio, status_imovel, limit, offset
    )


@router.get(
    "/propriedades/stats",
    summary="Contagem de propriedades por UF",
)
def stats(db: Session = Depends(get_db)):
    return banco_controller.stats_por_uf(db)


@router.get(
    "/propriedades/car/{cod_imovel:path}",
    response_model=PropriedadeResponse,
    summary="Buscar por código CAR",
    responses={404: {"description": "Propriedade não encontrada"}},
)
def buscar_por_car(cod_imovel: str, db: Session = Depends(get_db)):
    return banco_controller.buscar_por_cod_imovel(cod_imovel, db)


@router.get(
    "/propriedades/{id}",
    response_model=PropriedadeResponse,
    summary="Buscar por ID interno",
    responses={404: {"description": "Propriedade não encontrada"}},
)
def buscar(id: int, db: Session = Depends(get_db)):
    return banco_controller.buscar_propriedade(id, db)


@router.post(
    "/propriedades",
    response_model=PropriedadeResponse,
    status_code=201,
    summary="Upsert de propriedade",
)
def upsert(payload: PropriedadeCreate, db: Session = Depends(get_db)):
    return banco_controller.upsert_propriedade(payload.model_dump(), db)


@router.delete(
    "/propriedades/{id}",
    summary="Deletar propriedade",
    responses={404: {"description": "Propriedade não encontrada"}},
)
def deletar(id: int, db: Session = Depends(get_db)):
    return banco_controller.deletar_propriedade(id, db)
