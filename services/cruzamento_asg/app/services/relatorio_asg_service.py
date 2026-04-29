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
    ProdesSobreposicao,
    RelatorioASGResponse,
    ResumoASG,
    SecaoAreasProtegidas,
    SecaoDesmatamento,
    SecaoPropriedade,
    SecaoQueimadas,
)


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
    """
    0–100: desmatamento relativo (até 40) + alertas DETER (até 20) + focos (até 30) + AP (até 10, placeholder).
    """
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
    total = p_desm + p_deter + p_focos + ap_peso
    score = min(100.0, round(total, 2))
    if score < 35:
        nivel = "baixo"
    elif score < 65:
        nivel = "medio"
    else:
        nivel = "alto"
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


async def _carregar_dados(
    cod_imovel: str, imovel: dict[str, Any]
) -> DadosBrutosRelatorio:
    sobr, prodes_list, deter, focos, ap = await asyncio.gather(
        gb.buscar_sobreposicao_prodes(cod_imovel),
        gb.buscar_prodes_por_propriedade(cod_imovel),
        gb.buscar_deter_por_propriedade(cod_imovel),
        gb.buscar_focos_por_propriedade(cod_imovel),
        gb.buscar_areas_protegidas_por_propriedade(cod_imovel),
    )
    return DadosBrutosRelatorio(
        imovel=imovel,
        sobr_prodes=sobr,
        prodes_poligonos=prodes_list,
        deter=deter or [],
        focos=focos or [],
        ap=ap or [],
    )


async def montar_relatorio(cod_imovel: str) -> tuple[RelatorioASGResponse, DadosBrutosRelatorio]:
    gerado = _dt_iso_utc()
    base_im = await gb.buscar_por_car(cod_imovel)
    if not base_im:
        bruto = DadosBrutosRelatorio(
            imovel=None,
            sobr_prodes={},
            prodes_poligonos=[],
            deter=[],
            focos=[],
            ap=[],
        )
        r = _relatorio_vazio(cod_imovel, gerado, bruto)
        return r, bruto
    d = await _carregar_dados(cod_imovel, base_im)
    n_pol = d.sobr_prodes.get("n_poligonos", 0) or 0
    area_ha = float(d.sobr_prodes.get("area_ha", 0) or 0)
    por_ano = d.sobr_prodes.get("por_ano", []) or []
    prodes_ano = max((x.get("ano") for x in por_ano if x.get("ano")), default=None)
    prodes_data_ref: str | None
    if prodes_ano is not None:
        prodes_data_ref = f"{int(prodes_ano)}-12-31"
    else:
        prodes_data_ref = _ref_max_ingerido(
            d.prodes_poligonos, gerado.date().isoformat()
        )
    n_deter = len(d.deter)
    ucs = sorted(
        {str(x.get("uc")) for x in d.deter if x.get("uc")}
    )
    deter_data_ref = _ref_max_ingerido(
        d.deter, gerado.date().isoformat()
    )
    n_focos = len(d.focos)
    focos_data_ref = _ref_max_ingerido(
        d.focos, gerado.date().isoformat()
    )
    n_ap = len(d.ap)
    area_imo = base_im.get("area")
    if area_imo is not None:
        try:
            area_imo = float(area_imo)
        except (TypeError, ValueError):
            area_imo = None
    score, nivel, rel, p_ap = calcular_indice_risco(
        area_imo, area_ha, n_deter, n_focos, n_ap
    )
    prop_data_ref: str | None
    pcri = base_im.get("dat_criacao")
    if isinstance(pcri, datetime):
        prop_data_ref = pcri.date().isoformat()
    elif isinstance(pcri, str):
        prop_data_ref = pcri[:10]
    else:
        prop_data_ref = None
    ing = base_im.get("ingerido_em")
    if ing is not None and prop_data_ref is None:
        if isinstance(ing, datetime):
            prop_data_ref = ing.date().isoformat()
        elif isinstance(ing, str):
            prop_data_ref = ing[:10]
    if prop_data_ref is None:
        prop_data_ref = gerado.date().isoformat()
    secoes = RelatorioASGResponse(
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
                nota="Sem dados: endpoint de integração (Task 8) ainda não configurado."
                if n_ap == 0
                else None,
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
        secoes.areas_protegidas.resumo.nota = None
        parsed = [_parse_dt(x.get("ingerido_em")) for x in d.ap]
        good = [p for p in parsed if p is not None]
        if good:
            secoes.areas_protegidas.resumo.data_referencia = max(good).date().isoformat()
    return secoes, d


def _relatorio_vazio(
    cod_imovel: str, gerado: datetime, bruto: DadosBrutosRelatorio
) -> RelatorioASGResponse:
    ref = gerado.date().isoformat()
    return RelatorioASGResponse(
        cod_imovel=cod_imovel,
        gerado_em=gerado,
        propriedade=SecaoPropriedade(
            fonte=FONTE_SICAR,
            data_referencia=ref,
            dados=None,
        ),
        desmatamento=SecaoDesmatamento(
            prodes=ProdesSobreposicao(
                fonte=FONTE_INPE_PRODES,
                data_referencia=ref,
            ),
            deter=DeterResumo(
                fonte=FONTE_INPE_DETER,
                data_referencia=ref,
            ),
        ),
        queimadas=SecaoQueimadas(
            resumo=FocosResumo(
                fonte=FONTE_INPE_FOCOS,
                data_referencia=ref,
            ),
        ),
        areas_protegidas=SecaoAreasProtegidas(
            resumo=AreasProtegidasResumo(
                fonte=FONTE_AP,
                data_referencia=ref,
                n_sobreposicoes=0,
                nota="Imóvel não encontrado; sem cruzamento espacial.",
            ),
        ),
        resumo_asg=ResumoASG(
            indice_risco=0.0,
            nivel="baixo",
            desmatamento_relativo=None,
            peso_ap=0.0,
        ),
    )
