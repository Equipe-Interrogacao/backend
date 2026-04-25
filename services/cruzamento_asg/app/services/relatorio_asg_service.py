"""
Gera relatório ASG estruturado para uma propriedade combinando dados de
INPE (PRODES, DETER, Queimadas) e Áreas Protegidas (UC, TI, Assentamento, Quilombola).
"""

import asyncio
from datetime import datetime, timezone

from app.clients.gerenciamento_banco_client import (
    buscar_areas_protegidas_por_propriedade,
    buscar_deter_por_propriedade,
    buscar_focos_por_propriedade,
    buscar_por_car,
    buscar_sobreposicao_prodes,
)
from app.schemas.relatorio_asg_schema import IndicadorASG, RelatorioASGResponse


def _status(valor: float | int, limiares: tuple[float, float]) -> str:
    """Retorna 'ok', 'atencao' ou 'critico' baseado em limiares (atencao, critico)."""
    if valor >= limiares[1]:
        return "critico"
    if valor >= limiares[0]:
        return "atencao"
    return "ok"


async def gerar_relatorio(cod_imovel: str) -> RelatorioASGResponse | None:
    prop, prodes, deter, focos, areas = await asyncio.gather(
        buscar_por_car(cod_imovel),
        buscar_sobreposicao_prodes(cod_imovel),
        buscar_deter_por_propriedade(cod_imovel),
        buscar_focos_por_propriedade(cod_imovel),
        buscar_areas_protegidas_por_propriedade(cod_imovel),
    )

    if not prop:
        return None

    indicadores: list[IndicadorASG] = []

    # ── Ambiental ──────────────────────────────────────────────────────────────

    prodes_ha = prodes.get("area_ha", 0.0) or 0.0
    prodes_n = prodes.get("n_poligonos", 0) or 0
    indicadores.append(IndicadorASG(
        categoria="Ambiental",
        nome="Desmatamento PRODES",
        fonte="INPE / PRODES",
        data_referencia="2008–2024",
        valor=round(prodes_ha, 2),
        unidade="ha",
        status=_status(prodes_ha, (0.01, 1.0)),
        detalhe=f"{prodes_n} polígono(s) sobrepostos" if prodes_n > 0 else None,
    ))

    deter_n = len(deter)
    indicadores.append(IndicadorASG(
        categoria="Ambiental",
        nome="Alertas DETER",
        fonte="INPE / DETER",
        data_referencia="2016–2024",
        valor=float(deter_n),
        unidade="alertas",
        status=_status(deter_n, (1, 3)),
        detalhe=None,
    ))

    focos_n = len(focos)
    indicadores.append(IndicadorASG(
        categoria="Ambiental",
        nome="Focos de Queimada",
        fonte="INPE / BDQueimadas",
        data_referencia="2016–2025",
        valor=float(focos_n),
        unidade="focos",
        status=_status(focos_n, (1, 5)),
        detalhe=None,
    ))

    # ── Social ─────────────────────────────────────────────────────────────────

    ucs = areas.get("uc", [])
    uc_n = len(ucs)
    indicadores.append(IndicadorASG(
        categoria="Social",
        nome="Unidades de Conservação",
        fonte="ICMBio / INDE",
        data_referencia="2026",
        valor=float(uc_n),
        unidade="UCs",
        status=_status(uc_n, (1, 1)),
        detalhe=", ".join(u.get("nome") or u.get("cod_uc", "") for u in ucs[:3]) or None,
    ))

    tis = areas.get("ti", [])
    ti_n = len(tis)
    indicadores.append(IndicadorASG(
        categoria="Social",
        nome="Terras Indígenas",
        fonte="FUNAI",
        data_referencia="2026",
        valor=float(ti_n),
        unidade="TIs",
        status=_status(ti_n, (1, 1)),
        detalhe=", ".join(
            f"{t.get('nome') or t.get('cod_ti', '')} ({t.get('etnia') or ''})"
            for t in tis[:3]
        ) or None,
    ))

    ass = areas.get("assentamento", [])
    ass_n = len(ass)
    indicadores.append(IndicadorASG(
        categoria="Social",
        nome="Assentamentos INCRA",
        fonte="INCRA / SIPAM",
        data_referencia="2026",
        valor=float(ass_n),
        unidade="assentamentos",
        status=_status(ass_n, (1, 2)),
        detalhe=", ".join(a.get("nome") or a.get("cod_sipra", "") for a in ass[:3]) or None,
    ))

    qui = areas.get("quilombola", [])
    qui_n = len(qui)
    indicadores.append(IndicadorASG(
        categoria="Social",
        nome="Territórios Quilombolas",
        fonte="FCP / SIPAM",
        data_referencia="2026",
        valor=float(qui_n),
        unidade="territórios",
        status=_status(qui_n, (1, 1)),
        detalhe=", ".join(q.get("nome") or q.get("cod_quilombola", "") for q in qui[:3]) or None,
    ))

    # ── Governança ─────────────────────────────────────────────────────────────

    status_car = prop.get("status_imovel") or "Desconhecido"
    car_status_asg = "ok" if status_car in ("AT", "Ativo") else "pendente" if status_car in ("PE", "CA") else "atencao"
    indicadores.append(IndicadorASG(
        categoria="Governança",
        nome="Status CAR",
        fonte="SICAR / SFB",
        data_referencia="2026",
        valor=None,
        unidade=None,
        status=car_status_asg,
        detalhe=status_car,
    ))

    return RelatorioASGResponse(
        cod_imovel=cod_imovel,
        municipio=prop.get("municipio"),
        uf=prop.get("uf"),
        area_ha=prop.get("area"),
        status_car=status_car,
        gerado_em=datetime.now(timezone.utc),
        indicadores=indicadores,
    )
