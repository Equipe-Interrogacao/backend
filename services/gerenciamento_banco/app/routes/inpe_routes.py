from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Any, Optional

from app.config.database import get_db
from app.controllers import inpe_controller
from app.schemas.inpe_schema import (
    AlertaDeterResponse,
    DesmatamentoProdesResponse,
    FocoQueimadaResponse,
)

router = APIRouter(prefix="/banco", tags=["INPE — Dados Ambientais"])


# ------------------------------------------------------------------ PRODES

@router.get(
    "/desmatamento-prodes",
    response_model=list[DesmatamentoProdesResponse],
    summary="Listar polígonos de desmatamento PRODES",
)
def listar_prodes(
    uf: Optional[str] = Query("SP", description="Sigla do estado"),
    ano: Optional[int] = Query(None, description="Ano de referência"),
    municipio: Optional[str] = Query(None, description="Nome parcial do município"),
    bioma: Optional[str] = Query(None, description="Nome parcial do bioma"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return inpe_controller.listar_prodes(db, uf, ano, municipio, bioma, limit, offset)


@router.get(
    "/desmatamento-prodes/stats",
    summary="Totais PRODES por ano",
)
def stats_prodes(
    uf: str = Query("SP"),
    db: Session = Depends(get_db),
):
    return inpe_controller.stats_prodes(db, uf)


@router.get(
    "/desmatamento-prodes/por-propriedade/{cod_imovel:path}",
    response_model=list[DesmatamentoProdesResponse],
    summary="PRODES que interceptam a propriedade (ST_Intersects)",
    description=(
        "Retorna os polígonos PRODES que têm sobreposição geométrica real com "
        "a propriedade indicada pelo código CAR. Usa ST_Intersects no PostGIS."
    ),
)
def prodes_por_propriedade(cod_imovel: str, db: Session = Depends(get_db)):
    return inpe_controller.listar_prodes_por_propriedade(cod_imovel, db)


@router.get(
    "/desmatamento-prodes/sobreposicao/{cod_imovel:path}",
    response_model=dict[str, Any],
    summary="Área de desmatamento DENTRO da propriedade (ST_Intersection)",
    description=(
        "Calcula a área real (ha) de desmatamento PRODES dentro do polígono da "
        "propriedade via ST_Intersection + ST_Area(geography). "
        "Retorna total e detalhamento por ano."
    ),
)
def sobreposicao_prodes(cod_imovel: str, db: Session = Depends(get_db)):
    return inpe_controller.sobreposicao_prodes_por_propriedade(cod_imovel, db)


@router.get(
    "/desmatamento-prodes/{id_poligono:path}",
    response_model=DesmatamentoProdesResponse,
    summary="Buscar polígono PRODES por ID",
    responses={404: {"description": "Não encontrado"}},
)
def buscar_prodes(id_poligono: str, db: Session = Depends(get_db)):
    return inpe_controller.buscar_prodes(id_poligono, db)


# ------------------------------------------------------------------- DETER

@router.get(
    "/alerta-deter",
    response_model=list[AlertaDeterResponse],
    summary="Listar alertas de desmatamento DETER",
)
def listar_deter(
    uf: Optional[str] = Query("SP", description="Sigla do estado"),
    ano: Optional[int] = Query(None, description="Ano de detecção (extraído de view_date)"),
    municipio: Optional[str] = Query(None, description="Nome parcial do município"),
    classname: Optional[str] = Query(None, description="Classe do alerta"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return inpe_controller.listar_deter(db, uf, ano, municipio, classname, limit, offset)


@router.get(
    "/alerta-deter/por-propriedade/{cod_imovel:path}",
    response_model=list[AlertaDeterResponse],
    summary="Alertas DETER que interceptam a propriedade (ST_Intersects)",
)
def deter_por_propriedade(cod_imovel: str, db: Session = Depends(get_db)):
    return inpe_controller.listar_deter_por_propriedade(cod_imovel, db)


@router.get(
    "/alerta-deter/{id_alerta:path}",
    response_model=AlertaDeterResponse,
    summary="Buscar alerta DETER por ID",
    responses={404: {"description": "Não encontrado"}},
)
def buscar_deter(id_alerta: str, db: Session = Depends(get_db)):
    return inpe_controller.buscar_deter(id_alerta, db)


# ------------------------------------------------------------------ FOCOS

@router.get(
    "/foco-queimada",
    response_model=list[FocoQueimadaResponse],
    summary="Listar focos de queimada BDQueimadas",
)
def listar_focos(
    estado: Optional[str] = Query("SP", description="Sigla do estado"),
    municipio: Optional[str] = Query(None, description="Nome parcial do município"),
    bioma: Optional[str] = Query(None, description="Nome parcial do bioma"),
    ano: Optional[int] = Query(None, description="Ano de detecção"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return inpe_controller.listar_focos(db, estado, municipio, bioma, ano, limit, offset)


@router.get(
    "/foco-queimada/por-propriedade/{cod_imovel:path}",
    response_model=list[FocoQueimadaResponse],
    summary="Focos DENTRO da propriedade (ST_Within)",
    description="Retorna focos de queimada cujo ponto está dentro do polígono da propriedade.",
)
def focos_por_propriedade(cod_imovel: str, db: Session = Depends(get_db)):
    return inpe_controller.listar_focos_por_propriedade(cod_imovel, db)


@router.get(
    "/foco-queimada/stats",
    summary="Total de focos por ano",
)
def stats_focos(
    estado: str = Query("SP"),
    db: Session = Depends(get_db),
):
    return inpe_controller.stats_focos(db, estado)


@router.get(
    "/foco-queimada/{id_foco:path}",
    response_model=FocoQueimadaResponse,
    summary="Buscar foco de queimada por ID",
    responses={404: {"description": "Não encontrado"}},
)
def buscar_foco(id_foco: str, db: Session = Depends(get_db)):
    return inpe_controller.buscar_foco(id_foco, db)
