"""
Controller para áreas protegidas (UC, TI, Assentamento, Quilombola).
Padrão idêntico ao inpe_controller.py.
"""

from fastapi import BackgroundTasks, HTTPException

from app.services import (
    icmbio_ingestao_service,
    funai_ingestao_service,
    incra_ingestao_service,
    fcp_ingestao_service,
)


# --------------------------------------------------------------------------- #
# UC — Unidades de Conservação (ICMBio)
# --------------------------------------------------------------------------- #

def iniciar_ingestao_uc(uf: str, background_tasks: BackgroundTasks):
    status = icmbio_ingestao_service.get_status()
    if status["rodando"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestão UC já está em execução para '{status['estado']}'.",
        )
    background_tasks.add_task(icmbio_ingestao_service.ingerir_estado, uf)
    return {
        "mensagem": f"Ingestão de Unidades de Conservação (ICMBio) para '{uf}' iniciada em background.",
        "dica": "Consulte GET /ingestao/areas-protegidas/uc/status para acompanhar o progresso.",
    }


def status_uc():
    return icmbio_ingestao_service.get_status()


# --------------------------------------------------------------------------- #
# TI — Terras Indígenas (FUNAI)
# --------------------------------------------------------------------------- #

def iniciar_ingestao_ti(uf: str, background_tasks: BackgroundTasks):
    status = funai_ingestao_service.get_status()
    if status["rodando"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestão TI já está em execução para '{status['estado']}'.",
        )
    background_tasks.add_task(funai_ingestao_service.ingerir_estado, uf)
    return {
        "mensagem": f"Ingestão de Terras Indígenas (FUNAI) para '{uf}' iniciada em background.",
        "dica": "Consulte GET /ingestao/areas-protegidas/ti/status para acompanhar o progresso.",
    }


def status_ti():
    return funai_ingestao_service.get_status()


# --------------------------------------------------------------------------- #
# Assentamento — INCRA
# --------------------------------------------------------------------------- #

def iniciar_ingestao_assentamento(uf: str, background_tasks: BackgroundTasks):
    status = incra_ingestao_service.get_status()
    if status["rodando"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestão Assentamento já está em execução para '{status['estado']}'.",
        )
    background_tasks.add_task(incra_ingestao_service.ingerir_estado, uf)
    return {
        "mensagem": f"Ingestão de Assentamentos (INCRA) para '{uf}' iniciada em background.",
        "dica": "Consulte GET /ingestao/areas-protegidas/assentamento/status para acompanhar o progresso.",
    }


def status_assentamento():
    return incra_ingestao_service.get_status()


# --------------------------------------------------------------------------- #
# Quilombola — FCP / INCRA
# --------------------------------------------------------------------------- #

def iniciar_ingestao_quilombola(uf: str, background_tasks: BackgroundTasks):
    status = fcp_ingestao_service.get_status()
    if status["rodando"]:
        raise HTTPException(
            status_code=409,
            detail=f"Ingestão Quilombola já está em execução para '{status['estado']}'.",
        )
    background_tasks.add_task(fcp_ingestao_service.ingerir_estado, uf)
    return {
        "mensagem": f"Ingestão de Territórios Quilombolas (FCP) para '{uf}' iniciada em background.",
        "dica": "Consulte GET /ingestao/areas-protegidas/quilombola/status para acompanhar o progresso.",
    }


def status_quilombola():
    return fcp_ingestao_service.get_status()


# --------------------------------------------------------------------------- #
# Rota genérica /{fonte}/status
# --------------------------------------------------------------------------- #

_FONTE_HANDLERS = {
    "uc": status_uc,
    "ti": status_ti,
    "assentamento": status_assentamento,
    "quilombola": status_quilombola,
}


def status_por_fonte(fonte: str):
    handler = _FONTE_HANDLERS.get(fonte.lower())
    if not handler:
        raise HTTPException(status_code=404, detail=f"Fonte '{fonte}' não encontrada.")
    return handler()
