"""
Endpoints da API INPE (PRODES, DETER e BDQueimadas).

Todos os endpoints de ingestão são assíncronos (BackgroundTasks)
e retornam 202 Accepted imediatamente.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.controllers import inpe_controller
from app.schemas.inpe_schemas import (
    AlertaDeterResponse,
    DesmatamentoProdesResponse,
    FocoQueimadaResponse,
    InpeIngestaoStatusResponse,
)

router = APIRouter(prefix="/ingestao/inpe", tags=["Ingestão — INPE"])


# --------------------------------------------------------------------------- #
# PRODES — desmatamento anual
# --------------------------------------------------------------------------- #

@router.post(
    "/prodes/ingerir",
    status_code=202,
    summary="Iniciar ingestão PRODES",
    description=(
        "Dispara a ingestão em background dos polígonos anuais de desmatamento "
        "do PRODES via WFS TerraBrasilis. "
        "O processo é idempotente — re-execuções atualizam registros existentes."
    ),
)
def iniciar_ingestao_prodes(
    estado: str = Query("SP", description="Sigla do estado (ex: SP)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    return inpe_controller.iniciar_ingestao_prodes(estado, background_tasks)


@router.get(
    "/prodes/status",
    response_model=InpeIngestaoStatusResponse,
    summary="Status da ingestão PRODES",
    description="Retorna o progresso atual (ou último resultado) da ingestão PRODES.",
)
def status_prodes():
    return inpe_controller.status_prodes()


# --------------------------------------------------------------------------- #
# DETER — alertas em tempo real
# --------------------------------------------------------------------------- #

@router.post(
    "/deter/ingerir",
    status_code=202,
    summary="Iniciar ingestão DETER",
    description=(
        "Dispara a ingestão em background dos alertas de desmatamento em tempo-real "
        "do DETER via WFS TerraBrasilis. Filtro por uf=SP. "
        "O processo é idempotente — re-execuções atualizam registros existentes."
    ),
)
def iniciar_ingestao_deter(
    estado: str = Query("SP", description="Sigla do estado (ex: SP)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    return inpe_controller.iniciar_ingestao_deter(estado, background_tasks)


@router.get(
    "/deter/status",
    response_model=InpeIngestaoStatusResponse,
    summary="Status da ingestão DETER",
    description="Retorna o progresso atual (ou último resultado) da ingestão DETER.",
)
def status_deter():
    return inpe_controller.status_deter()


# --------------------------------------------------------------------------- #
# Queimadas — focos de incêndio
# --------------------------------------------------------------------------- #

@router.post(
    "/queimadas/ingerir",
    status_code=202,
    summary="Iniciar ingestão BDQueimadas",
    description=(
        "Dispara a ingestão em background dos focos de incêndio do BDQueimadas "
        "filtrados por estado e intervalo de anos (ano_inicio a ano_fim). "
        "Itera cada ano sequencialmente via WFS TerraBrasilis. "
        "O processo é idempotente — re-execuções atualizam registros existentes."
    ),
)
def iniciar_ingestao_queimadas(
    estado: str = Query("SP", description="Sigla do estado (ex: SP)"),
    ano_inicio: int = Query(2016, description="Ano de início do intervalo (ex: 2016)"),
    ano_fim: int = Query(2026, description="Ano de fim do intervalo (ex: 2026)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    return inpe_controller.iniciar_ingestao_queimadas(estado, ano_inicio, ano_fim, background_tasks)


@router.get(
    "/queimadas/status",
    response_model=InpeIngestaoStatusResponse,
    summary="Status da ingestão BDQueimadas",
    description="Retorna o progresso atual (ou último resultado) da ingestão BDQueimadas.",
)
def status_queimadas():
    return inpe_controller.status_queimadas()


# --------------------------------------------------------------------------- #
# Status genérico por fonte  GET /ingestao/inpe/{fonte}/status
# --------------------------------------------------------------------------- #

_FONTES_VALIDAS = {"prodes", "deter", "queimadas"}


@router.get(
    "/{fonte}/status",
    response_model=InpeIngestaoStatusResponse,
    summary="Status da ingestão por fonte INPE",
    description=(
        "Retorna o status da última (ou atual) ingestão para a fonte especificada. "
        "Fontes válidas: prodes, deter, queimadas."
    ),
)
def status_por_fonte(fonte: str):
    fonte = fonte.lower()
    if fonte not in _FONTES_VALIDAS:
        raise HTTPException(
            status_code=404,
            detail=f"Fonte '{fonte}' inválida. Use: {', '.join(sorted(_FONTES_VALIDAS))}",
        )
    return inpe_controller.status_por_fonte(fonte)
