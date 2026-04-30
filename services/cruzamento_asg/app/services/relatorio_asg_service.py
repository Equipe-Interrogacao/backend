"""
Dois servicos de relatorio ASG:
  - montar_relatorio()  -> Task 9: consolidado com secoes, indice de risco, export GPKG
  - gerar_relatorio()   -> Task 10: cards de indicadores para o frontend
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.clients import gerenciamento_banco_client as gb
from app.schemas.relatorio_asg_schema import (
    FONTE_AP,
    FONTE_INPE_DETER,
    FONTE_INPE_FOCOS,
    FONTE_INPE_PRODES,
    FONTE_SICAR,
    AreasProtegidasResumo,
    DadosPropriedadeSICAR,
    DeterResumo,
    FocosResumo,
    IndicadorASG,
    ProdesSobreposicao,
    RelatorioASGResponse,
    RelatorioIndicadoresResponse,
    ResumoASG,
    SecaoAreasProtegidas,
    SecaoDesmatamento,
    SecaoPropriedade,
    SecaoQueimadas,
)

# --- Task 9 - Relatorio consolidado ---


@dataclass
class DadosBrutosRelatorio:
    imovel: dict[str, Any] | None
    sobr_prodes: dict[str, Any]
    prodes_poligonos: list[dict[str, Any]]
    deter: list[dict[str, Any]]
    focos: list[dict[str, Any]]
    ap: list[dict[str, Any]]


def _dt_iso_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v
    if isinstance(v, str) and v.strip():
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _ref_max_ingerido(rows: list[dict[str, Any]], fallback: str | None) -> str | None:
    dates: list[datetime] = []
    for r in rows:
        t = _parse_dt(r.get("ingerido_em"))
        if t is not None:
            dates.append(t)
    if not dates and fallback:
        return fallback
    if dates:
        return max(dates).date().isoformat()
    return fallback


def _strip_geo(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in r.items() if k != "geometria"} for r in rows]


def calcular_indice_risco(
    area_prop_ha: float | None,
    area_desmat_ha: float,
    n_deter: int,
    n_focos: int,
    n_ap: int,
) -> tuple[float, str, float | None, float]:
    ap_peso = min(10.0, n_ap * 5.0)
    rel: float | None
    p_desm = 0.0
    if area_prop_ha and area_prop_ha > 0:
        rel = min(1.0, area_desmat_ha / area_prop_ha)
        p_desm = min(40.0, 40.0 * rel)
    else:
        rel = None
        p_desm = min(40.0, area_desmat_ha * 0.1)
    p_deter = min(20.0, n_deter * 2.0)
    p_focos = min(30.0, n_focos * 3.0)
    score = min(100.0, round(p_desm + p_deter + p_focos + ap_peso, 2))
    nivel = "baixo" if score < 35 else "medio" if score < 65 else "alto"
    return score, nivel, rel, ap_peso


def _propriedade_dados(imovel: dict[str, Any] | None) -> DadosPropriedadeSICAR | None:
    if not imovel:
        return None
    return DadosPropriedadeSICAR(
        cod_imovel=imovel.get("cod_imovel"),
        uf=imovel.get("uf"),
        municipio=imovel.get("municipio"),
        status_imovel=imovel.get("status_imovel"),
        area_ha=imovel.get("area"),
        condicao=imovel.get("condicao"),
        dat_criacao=imovel.get("dat_criacao"),
        ingerido_em=imovel.get("ingerido_em"),
        possui_geometria=bool(imovel.get("geometria")),
    )


async def _carregar_dados(cod_imovel: str, imovel: dict[str, Any]) -> DadosBrutosRelatorio:
    sobr, prodes_list, deter, focos, ap_dict = await asyncio.gather(
        gb.buscar_sobreposicao_prodes(cod_imovel),
        gb.buscar_prodes_por_propriedade(cod_imovel),
        gb.buscar_deter_por_propriedade(cod_imovel),
        gb.buscar_focos_por_propriedade(cod_imovel),
        gb.buscar_areas_protegidas_por_propriedade(cod_imovel),
    )
    # Achata dict {"uc": [...], "ti": [...], ...} em lista plana para o export
    ap_list: list[dict[str, Any]] = [item for lst in ap_dict.values() for item in lst]
    return DadosBrutosRelatorio(
        imovel=imovel,
        sobr_prodes=sobr,
        prodes_poligonos=prodes_list,
        deter=deter or [],
        focos=focos or [],
        ap=ap_list,
    )


async def montar_relatorio(cod_imovel: str) -> tuple[RelatorioASGResponse, DadosBrutosRelatorio]:
    gerado = _dt_iso_utc()
    base_im = await gb.buscar_por_car(cod_imovel)

    if not base_im:
        bruto = DadosBrutosRelatorio(
            imovel=None, sobr_prodes={}, prodes_poligonos=[], deter=[], focos=[], ap=[]
        )
        return _relatorio_vazio(cod_imovel, gerado, bruto), bruto

    d = await _carregar_dados(cod_imovel, base_im)
    n_pol = d.sobr_prodes.get("n_poligonos", 0) or 0
    area_ha = float(d.sobr_prodes.get("area_ha", 0) or 0)
    por_ano = d.sobr_prodes.get("por_ano", []) or []

    prodes_ano = max((x.get("ano") for x in por_ano if x.get("ano")), default=None)
    prodes_data_ref = (
        f"{int(prodes_ano)}-12-31"
        if prodes_ano
        else _ref_max_ingerido(d.prodes_poligonos, gerado.date().isoformat())
    )

    n_deter = len(d.deter)
    ucs = sorted({str(x.get("uc")) for x in d.deter if x.get("uc")})
    deter_data_ref = _ref_max_ingerido(d.deter, gerado.date().isoformat())

    n_focos = len(d.focos)
    focos_data_ref = _ref_max_ingerido(d.focos, gerado.date().isoformat())

    n_ap = len(d.ap)

    area_imo = base_im.get("area")
    try:
        area_imo = float(area_imo) if area_imo is not None else None
    except (TypeError, ValueError):
        area_imo = None

    score, nivel, rel, p_ap = calcular_indice_risco(area_imo, area_ha, n_deter, n_focos, n_ap)

    pcri = base_im.get("dat_criacao")
    if isinstance(pcri, datetime):
        prop_data_ref = pcri.date().isoformat()
    elif isinstance(pcri, str):
        prop_data_ref = pcri[:10]
    else:
        ing = base_im.get("ingerido_em")
        if isinstance(ing, datetime):
            prop_data_ref = ing.date().isoformat()
        elif isinstance(ing, str):
            prop_data_ref = ing[:10]
        else:
            prop_data_ref = gerado.date().isoformat()

    relatorio = RelatorioASGResponse(
        cod_imovel=cod_imovel,
        gerado_em=gerado,
        propriedade=SecaoPropriedade(
            fonte=FONTE_SICAR,
            data_referencia=prop_data_ref,
            dados=_propriedade_dados(base_im),
        ),
        desmatamento=SecaoDesmatamento(
            prodes=ProdesSobreposicao(
                fonte=FONTE_INPE_PRODES,
                data_referencia=prodes_data_ref,
                n_poligonos=n_pol,
                area_sobreposta_ha=area_ha,
                por_ano=por_ano,
            ),
            deter=DeterResumo(
                fonte=FONTE_INPE_DETER,
                data_referencia=deter_data_ref,
                n_alertas=n_deter,
                ucs_mencionadas=ucs,
            ),
            alertas_deter=_strip_geo(d.deter),
            poligonos_prodes=_strip_geo(d.prodes_poligonos),
        ),
        queimadas=SecaoQueimadas(
            resumo=FocosResumo(
                fonte=FONTE_INPE_FOCOS,
                data_referencia=focos_data_ref,
                n_focos=n_focos,
            ),
            focos=_strip_geo(d.focos),
        ),
        areas_protegidas=SecaoAreasProtegidas(
            resumo=AreasProtegidasResumo(
                fonte=FONTE_AP,
                data_referencia=gerado.date().isoformat() if n_ap == 0 else None,
                n_sobreposicoes=n_ap,
                nota="Sem sobreposicoes com areas protegidas." if n_ap == 0 else None,
            ),
            feicoes=_strip_geo(d.ap),
        ),
        resumo_asg=ResumoASG(
            indice_risco=score,
            nivel=nivel,
            desmatamento_relativo=rel,
            peso_ap=p_ap,
        ),
    )

    if n_ap:
        relatorio.areas_protegidas.resumo.nota = None
        parsed = [_parse_dt(x.get("ingerido_em")) for x in d.ap]
        good = [p for p in parsed if p is not None]
        if good:
            relatorio.areas_protegidas.resumo.data_referencia = max(good).date().isoformat()

    return relatorio, d


def _relatorio_vazio(
    cod_imovel: str, gerado: datetime, bruto: DadosBrutosRelatorio
) -> RelatorioASGResponse:
    ref = gerado.date().isoformat()
    return RelatorioASGResponse(
        cod_imovel=cod_imovel,
        gerado_em=gerado,
        propriedade=SecaoPropriedade(fonte=FONTE_SICAR, data_referencia=ref, dados=None),
        desmatamento=SecaoDesmatamento(
            prodes=ProdesSobreposicao(fonte=FONTE_INPE_PRODES, data_referencia=ref),
            deter=DeterResumo(fonte=FONTE_INPE_DETER, data_referencia=ref),
        ),
        queimadas=SecaoQueimadas(
            resumo=FocosResumo(fonte=FONTE_INPE_FOCOS, data_referencia=ref),
        ),
        areas_protegidas=SecaoAreasProtegidas(
            resumo=AreasProtegidasResumo(
                fonte=FONTE_AP,
                data_referencia=ref,
                nota="Imovel nao encontrado.",
            ),
        ),
        resumo_asg=ResumoASG(
            indice_risco=0.0,
            nivel="baixo",
            desmatamento_relativo=None,
            peso_ap=0.0,
        ),
    )


# --- Task 10 - Cards de indicadores para o frontend ---


def _status(valor: float | int, limiares: tuple[float, float]) -> str:
    if valor >= limiares[1]:
        return "critico"
    if valor >= limiares[0]:
        return "atencao"
    return "ok"


async def gerar_relatorio(cod_imovel: str) -> RelatorioIndicadoresResponse | None:
    prop, prodes, deter, focos, areas = await asyncio.gather(
        gb.buscar_por_car(cod_imovel),
        gb.buscar_sobreposicao_prodes(cod_imovel),
        gb.buscar_deter_por_propriedade(cod_imovel),
        gb.buscar_focos_por_propriedade(cod_imovel),
        gb.buscar_areas_protegidas_por_propriedade(cod_imovel),
    )

    if not prop:
        return None

    indicadores: list[IndicadorASG] = []

    prodes_ha = prodes.get("area_ha", 0.0) or 0.0
    prodes_n = prodes.get("n_poligonos", 0) or 0
    indicadores.append(IndicadorASG(
        categoria="Ambiental", nome="Desmatamento PRODES", fonte="INPE / PRODES",
        data_referencia="2008-2024", valor=round(prodes_ha, 2), unidade="ha",
        status=_status(prodes_ha, (0.01, 1.0)),
        detalhe=f"{prodes_n} poligono(s) sobrepostos" if prodes_n > 0 else None,
    ))

    deter_n = len(deter)
    indicadores.append(IndicadorASG(
        categoria="Ambiental", nome="Alertas DETER", fonte="INPE / DETER",
        data_referencia="2016-2024", valor=float(deter_n), unidade="alertas",
        status=_status(deter_n, (1, 3)), detalhe=None,
    ))

    focos_n = len(focos)
    indicadores.append(IndicadorASG(
        categoria="Ambiental", nome="Focos de Queimada", fonte="INPE / BDQueimadas",
        data_referencia="2016-2025", valor=float(focos_n), unidade="focos",
        status=_status(focos_n, (1, 5)), detalhe=None,
    ))

    ucs = areas.get("uc", [])
    uc_n = len(ucs)
    indicadores.append(IndicadorASG(
        categoria="Social", nome="Unidades de Conservacao", fonte="ICMBio / INDE",
        data_referencia="2026", valor=float(uc_n), unidade="UCs",
        status=_status(uc_n, (1, 1)),
        detalhe=", ".join(u.get("nome") or u.get("cod_uc", "") for u in ucs[:3]) or None,
    ))

    tis = areas.get("ti", [])
    ti_n = len(tis)
    indicadores.append(IndicadorASG(
        categoria="Social", nome="Terras Indigenas", fonte="FUNAI",
        data_referencia="2026", valor=float(ti_n), unidade="TIs",
        status=_status(ti_n, (1, 1)),
        detalhe=", ".join(
            f"{t.get('nome') or t.get('cod_ti', '')} ({t.get('etnia') or ''})"
            for t in tis[:3]
        ) or None,
    ))

    ass = areas.get("assentamento", [])
    ass_n = len(ass)
    indicadores.append(IndicadorASG(
        categoria="Social", nome="Assentamentos INCRA", fonte="INCRA / SIPAM",
        data_referencia="2026", valor=float(ass_n), unidade="assentamentos",
        status=_status(ass_n, (1, 2)),
        detalhe=", ".join(a.get("nome") or a.get("cod_sipra", "") for a in ass[:3]) or None,
    ))

    qui = areas.get("quilombola", [])
    qui_n = len(qui)
    indicadores.append(IndicadorASG(
        categoria="Social", nome="Territorios Quilombolas", fonte="FCP / SIPAM",
        data_referencia="2026", valor=float(qui_n), unidade="territorios",
        status=_status(qui_n, (1, 1)),
        detalhe=", ".join(q.get("nome") or q.get("cod_quilombola", "") for q in qui[:3]) or None,
    ))

    status_car = prop.get("status_imovel") or "Desconhecido"
    car_status_asg = (
        "ok" if status_car in ("AT", "Ativo")
        else "pendente" if status_car in ("PE", "CA")
        else "atencao"
    )
    indicadores.append(IndicadorASG(
        categoria="Governanca", nome="Status CAR", fonte="SICAR / SFB",
        data_referencia="2026", valor=None, unidade=None,
        status=car_status_asg, detalhe=status_car,
    ))

    return RelatorioIndicadoresResponse(
        cod_imovel=cod_imovel,
        municipio=prop.get("municipio"),
        uf=prop.get("uf"),
        area_ha=prop.get("area"),
        status_car=status_car,
        gerado_em=datetime.now(timezone.utc),
        indicadores=indicadores,
    )
