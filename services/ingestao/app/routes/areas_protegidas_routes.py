"""
Endpoints de ingestão de Áreas Protegidas (UC, TI, Assentamento, Quilombola).
Padrão idêntico ao inpe_routes.py.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.controllers import areas_protegidas_controller
from app.schemas.areas_protegidas_schemas import AreasProtegidasIngestaoStatusResponse

router = APIRouter(prefix="/ingestao/areas-protegidas", tags=["Ingestão — Áreas Protegidas"])

_FONTES_VALIDAS = {"uc", "ti", "assentamento", "quilombola"}


# --------------------------------------------------------------------------- #
# UC — Unidades de Conservação (ICMBio)
# --------------------------------------------------------------------------- #

@router.post(
    "/uc/ingerir",
    status_code=202,
    summary="Iniciar ingestão de Unidades de Conservação (ICMBio)",
    description=(
        "Dispara em background a ingestão de UCs federais via WFS ICMBio (SMCUC:ucstodas). "
        "Filtro por siglaUF contendo a sigla do estado. Upsert idempotente por codigoCnuc."
    ),
)
def iniciar_uc(
    uf: str = Query("SP", description="Sigla do estado (ex: SP)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    return areas_protegidas_controller.iniciar_ingestao_uc(uf, background_tasks)


@router.get(
    "/uc/status",
    response_model=AreasProtegidasIngestaoStatusResponse,
    summary="Status da ingestão de UCs",
)
def status_uc():
    return areas_protegidas_controller.status_uc()


# --------------------------------------------------------------------------- #
# TI — Terras Indígenas (FUNAI)
# --------------------------------------------------------------------------- #

@router.post(
    "/ti/ingerir",
    status_code=202,
    summary="Iniciar ingestão de Terras Indígenas (FUNAI)",
    description=(
        "Dispara em background a ingestão de TIs via WFS FUNAI (Funai:tis_poligonais). "
        "Filtro por uf_sigla. Upsert idempotente por terrai_cod."
    ),
)
def iniciar_ti(
    uf: str = Query("SP", description="Sigla do estado (ex: SP)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    return areas_protegidas_controller.iniciar_ingestao_ti(uf, background_tasks)


@router.get(
    "/ti/status",
    response_model=AreasProtegidasIngestaoStatusResponse,
    summary="Status da ingestão de TIs",
)
def status_ti():
    return areas_protegidas_controller.status_ti()


# --------------------------------------------------------------------------- #
# Assentamento — INCRA
# --------------------------------------------------------------------------- #

@router.post(
    "/assentamento/ingerir",
    status_code=202,
    summary="Iniciar ingestão de Assentamentos (INCRA)",
    description=(
        "Dispara em background a ingestão de projetos de assentamento via WFS INCRA. "
        "Filtro por sg_uf. Upsert idempotente por cd_sipra."
    ),
)
def iniciar_assentamento(
    uf: str = Query("SP", description="Sigla do estado (ex: SP)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    return areas_protegidas_controller.iniciar_ingestao_assentamento(uf, background_tasks)


@router.get(
    "/assentamento/status",
    response_model=AreasProtegidasIngestaoStatusResponse,
    summary="Status da ingestão de Assentamentos",
)
def status_assentamento():
    return areas_protegidas_controller.status_assentamento()


# --------------------------------------------------------------------------- #
# Quilombola — FCP / INCRA
# --------------------------------------------------------------------------- #

@router.post(
    "/quilombola/ingerir",
    status_code=202,
    summary="Iniciar ingestão de Territórios Quilombolas (FCP)",
    description=(
        "Dispara em background a ingestão de territórios quilombolas via WFS INCRA. "
        "Filtro por sg_uf. Upsert idempotente por nr_processo."
    ),
)
def iniciar_quilombola(
    uf: str = Query("SP", description="Sigla do estado (ex: SP)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    return areas_protegidas_controller.iniciar_ingestao_quilombola(uf, background_tasks)


@router.get(
    "/quilombola/status",
    response_model=AreasProtegidasIngestaoStatusResponse,
    summary="Status da ingestão de Quilombolas",
)
def status_quilombola():
    return areas_protegidas_controller.status_quilombola()


# --------------------------------------------------------------------------- #
# Status genérico por fonte
# --------------------------------------------------------------------------- #

@router.get(
    "/{fonte}/status",
    response_model=AreasProtegidasIngestaoStatusResponse,
    summary="Status da ingestão por fonte de área protegida",
    description="Fontes válidas: uc, ti, assentamento, quilombola.",
)
def status_por_fonte(fonte: str):
    fonte = fonte.lower()
    if fonte not in _FONTES_VALIDAS:
        raise HTTPException(
            status_code=404,
            detail=f"Fonte '{fonte}' inválida. Use: {', '.join(sorted(_FONTES_VALIDAS))}",
        )
    return areas_protegidas_controller.status_por_fonte(fonte)
