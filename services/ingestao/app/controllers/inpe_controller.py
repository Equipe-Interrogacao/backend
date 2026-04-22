"""
Controller para as fontes INPE (PRODES, DETER e BDQueimadas).

Orquestra os BackgroundTasks e expõe o status de cada serviço de ingestão.
Segue o mesmo padrão de ingestao_controller.py.
"""

from datetime import datetime
from fastapi import BackgroundTasks, HTTPException

from app.services import (
    inpe_prodes_ingestao_service,
    inpe_deter_ingestao_service,
    inpe_queimadas_ingestao_service,
)


# --------------------------------------------------------------------------- #
# PRODES
# --------------------------------------------------------------------------- #

def iniciar_ingestao_prodes(estado: str, background_tasks: BackgroundTasks):
    status = inpe_prodes_ingestao_service.get_status()
    if status["rodando"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestão PRODES já está em execução para '{status['estado']}'.",
        )
    background_tasks.add_task(inpe_prodes_ingestao_service.ingerir_estado, estado)
    return {
        "mensagem": f"Ingestão PRODES do estado '{estado}' iniciada em background.",
        "dica": "Consulte GET /ingestao/inpe/prodes/status para acompanhar o progresso.",
    }


def status_prodes():
    return inpe_prodes_ingestao_service.get_status()


# --------------------------------------------------------------------------- #
# DETER
# --------------------------------------------------------------------------- #

def iniciar_ingestao_deter(estado: str, background_tasks: BackgroundTasks):
    status = inpe_deter_ingestao_service.get_status()
    if status["rodando"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestão DETER já está em execução para '{status['estado']}'.",
        )
    background_tasks.add_task(inpe_deter_ingestao_service.ingerir_estado, estado)
    return {
        "mensagem": f"Ingestão DETER do estado '{estado}' iniciada em background.",
        "dica": "Consulte GET /ingestao/inpe/deter/status para acompanhar o progresso.",
    }


def status_deter():
    return inpe_deter_ingestao_service.get_status()


# --------------------------------------------------------------------------- #
# Queimadas
# --------------------------------------------------------------------------- #

def iniciar_ingestao_queimadas(
    estado: str,
    ano_inicio: int,
    ano_fim: int,
    background_tasks: BackgroundTasks,
):
    status = inpe_queimadas_ingestao_service.get_status()
    if status["rodando"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestão BDQueimadas já está em execução para '{status['estado']}'.",
        )
    background_tasks.add_task(
        inpe_queimadas_ingestao_service.ingerir_estado,
        estado,
        ano_inicio,
        ano_fim,
    )
    return {
        "mensagem": (
            f"Ingestão BDQueimadas do estado '{estado}' "
            f"(anos {ano_inicio}–{ano_fim}) iniciada em background."
        ),
        "dica": "Consulte GET /ingestao/inpe/queimadas/status para acompanhar o progresso.",
    }


def status_queimadas():
    return inpe_queimadas_ingestao_service.get_status()


# --------------------------------------------------------------------------- #
# Rota genérica /{fonte}/status
# --------------------------------------------------------------------------- #

_FONTE_HANDLERS = {
    "prodes": status_prodes,
    "deter": status_deter,
    "queimadas": status_queimadas,
}


def status_por_fonte(fonte: str):
    handler = _FONTE_HANDLERS.get(fonte.lower())
    if not handler:
        raise HTTPException(status_code=404, detail=f"Fonte '{fonte}' não encontrada.")
    return handler()
