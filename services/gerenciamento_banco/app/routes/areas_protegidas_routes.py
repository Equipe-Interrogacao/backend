from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.controllers import areas_protegidas_controller
from app.schemas.areas_protegidas_schema import (
    AssentamentoResponse,
    QuilombolaResponse,
    TerraIndigenaResponse,
    UnidadeConservacaoResponse,
)

router = APIRouter(prefix="/banco", tags=["Áreas Protegidas"])


@router.get(
    "/unidade-conservacao",
    response_model=list[UnidadeConservacaoResponse],
    summary="Listar Unidades de Conservação",
)
def listar_ucs(
    uf: Optional[str] = Query("SP"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    return areas_protegidas_controller.listar_ucs(db, uf, limit)


@router.get(
    "/terra-indigena",
    response_model=list[TerraIndigenaResponse],
    summary="Listar Terras Indígenas",
)
def listar_tis(
    uf: Optional[str] = Query("SP"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    return areas_protegidas_controller.listar_tis(db, uf, limit)


@router.get(
    "/assentamento",
    response_model=list[AssentamentoResponse],
    summary="Listar Assentamentos",
)
def listar_assentamentos(
    uf: Optional[str] = Query("SP"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    return areas_protegidas_controller.listar_assentamentos(db, uf, limit)


@router.get(
    "/quilombola",
    response_model=list[QuilombolaResponse],
    summary="Listar Territórios Quilombolas",
)
def listar_quilombolas(
    uf: Optional[str] = Query("SP"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    return areas_protegidas_controller.listar_quilombolas(db, uf, limit)


@router.get(
    "/unidade-conservacao/por-propriedade/{cod_imovel:path}",
    response_model=list[UnidadeConservacaoResponse],
    summary="UCs que interceptam a propriedade (ST_Intersects)",
)
def ucs_por_propriedade(cod_imovel: str, db: Session = Depends(get_db)):
    return areas_protegidas_controller.ucs_por_propriedade(cod_imovel, db)


@router.get(
    "/terra-indigena/por-propriedade/{cod_imovel:path}",
    response_model=list[TerraIndigenaResponse],
    summary="Terras Indígenas que interceptam a propriedade (ST_Intersects)",
)
def tis_por_propriedade(cod_imovel: str, db: Session = Depends(get_db)):
    return areas_protegidas_controller.tis_por_propriedade(cod_imovel, db)


@router.get(
    "/assentamento/por-propriedade/{cod_imovel:path}",
    response_model=list[AssentamentoResponse],
    summary="Assentamentos que interceptam a propriedade (ST_Intersects)",
)
def assentamentos_por_propriedade(cod_imovel: str, db: Session = Depends(get_db)):
    return areas_protegidas_controller.assentamentos_por_propriedade(cod_imovel, db)


@router.get(
    "/quilombola/por-propriedade/{cod_imovel:path}",
    response_model=list[QuilombolaResponse],
    summary="Territórios Quilombolas que interceptam a propriedade (ST_Intersects)",
)
def quilombolas_por_propriedade(cod_imovel: str, db: Session = Depends(get_db)):
    return areas_protegidas_controller.quilombolas_por_propriedade(cod_imovel, db)
