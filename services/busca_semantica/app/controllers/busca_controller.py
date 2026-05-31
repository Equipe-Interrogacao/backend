import asyncio
import re
from sqlalchemy.orm import Session

from app.services.busca_service import BuscaService
from app.schemas.consulta_schema import ConsultaCreate
from app.services import nlp_service
from app.clients.cruzamento_client import chamar_cruzamento
from app.clients.relatorio_client import obter_relatorio_car
from app.clients.gerenciamento_banco_client import (
    buscar_por_car,
    buscar_areas_protegidas_por_propriedade,
    buscar_stats_inpe_por_propriedade,
    buscar_propriedades_proximas,
    buscar_propriedades_por_municipio,
    buscar_ranking_municipios,
)

_RANKING_RE = re.compile(
    r"\b(qual|quais|onde|cidade|municipio|município|cidades|municip|ranking|top|mais|maior|maior\s+numero|mais\s+registros)\b",
    re.IGNORECASE,
)

service = BuscaService()


async def realizar_consulta(payload: ConsultaCreate, db: Session):
    pergunta = payload.pergunta
    cod_car_from_question = nlp_service.extrair_cod_imovel(pergunta)
    cod_car = cod_car_from_question or payload.cod_car

    intencao, confianca, matches, _intencao_corr = nlp_service.extrair_intencao(pergunta)
    municipio, _municipio_corr = nlp_service.extrair_municipio(pergunta)
    coordenadas = nlp_service.extrair_coordenadas(pergunta)

    # Nota de correção ortográfica (ex: "Você quis dizer: *queimadaas* → **queimadas**?")
    _corr_parts = []
    if _intencao_corr:
        _corr_parts.append(f"*{_intencao_corr[0]}* → **{_intencao_corr[1]}**")
    if _municipio_corr:
        _corr_parts.append(f"*{_municipio_corr[0]}* → **{_municipio_corr[1]}**")
    _nota_correcao = ("Você quis dizer: " + ", ".join(_corr_parts) + "?\n\n") if _corr_parts else ""

    # Sinal real detectado na query atual (antes de aplicar contexto)
    _has_query_signal = bool(intencao or municipio or coordenadas or cod_car_from_question)

    # Queries analíticas (ranking, comparação) não herdam contexto de localidade
    _is_analytical = bool(_RANKING_RE.search(pergunta))
    if _is_analytical and not cod_car_from_question:
        cod_car = None

    # Contexto da mensagem anterior como fallback (apenas para follow-ups não analíticos)
    # Só aplica contexto se a query atual tem pelo menos um sinal real —
    # evita que lixo ("asd em asdhasu") herde contexto e pareça uma resposta válida
    municipio_from_context = False
    if _has_query_signal and not municipio and payload.municipio_contexto and not _is_analytical:
        municipio = payload.municipio_contexto
        municipio_from_context = True
    if _has_query_signal and not intencao and payload.intencao_contexto and not _is_analytical:
        intencao = payload.intencao_contexto
        confianca = 0.5

    # Novo município explicitamente mencionado → não usar o CAR do payload
    # (usuário quer trocar de contexto espacial, não continuar na propriedade anterior)
    if municipio and not municipio_from_context and not cod_car_from_question:
        cod_car = None

    resposta_text = ""
    dados = None
    acao = None

    # Confiança muito baixa sem contexto → pede esclarecimento em vez de responder errado
    # Não aplica se município foi detectado — ex: "Queimadas em Caraguatatuba" é inequívoco
    if intencao and confianca < 0.20 and not payload.intencao_contexto and not municipio:
        _INTENT_LABELS_CONF = {
            "queimada": "queimadas", "desmatamento": "desmatamento PRODES",
            "alerta": "alertas DETER", "indigena": "terras indígenas",
            "conservacao": "unidades de conservação", "comunidades": "assentamentos/quilombolas",
            "relatorio": "relatório ASG", "governanca": "governança/CAR", "fundiario": "fundiário",
        }
        guess = _INTENT_LABELS_CONF.get(intencao, intencao)
        resposta_text = (
            f"Não entendi completamente. Você quer consultar **{guess}**?\n\n"
            "Pode reformular ou escolher diretamente:\n"
            "  • **Desmatamento** — *tem PRODES nessa fazenda?*\n"
            "  • **Queimadas** — *houve foco de calor aqui?*\n"
            "  • **Alertas DETER** — *tem degradação ativa?*\n"
            "  • **Terras Indígenas / UCs** — *tem sobreposição com TI?*\n"
            "  • **Relatório ASG** — *qual o risco ASG da propriedade?*\n"
            "  • **Município** — *queimadas em Campinas*"
        )
        consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)
        return _montar_resposta(consulta_obj, pergunta, resposta_text, cod_car,
                                None, 0.0, dados, None, municipio, None, _nota_correcao)

    # ── Query de ranking por município ───────────────────────────────────────
    _INTENT_FONTE_MAP = {
        "alerta":       "deter",
        "desmatamento": "prodes",
        "queimada":     "focos",
    }

    # Ranking de risco não existe por município — redireciona com contexto útil
    if intencao == "relatorio" and _is_analytical and not cod_car:
        resposta_text = (
            "Não tenho um ranking de risco ASG por município — esse índice é calculado "
            "propriedade a propriedade.\n\n"
            "Posso mostrar rankings por indicador específico:\n"
            "  • **Focos de queimada** — *qual cidade tem mais queimadas?*\n"
            "  • **Desmatamento PRODES** — *qual município tem mais desmatamento?*\n"
            "  • **Alertas DETER** — *onde há mais alertas de degradação?*\n\n"
            "Para ver o risco ASG de uma propriedade, informe o **código CAR** "
            "ou mencione um **município** e selecione uma propriedade."
        )
        consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)
        return _montar_resposta(consulta_obj, pergunta, resposta_text, cod_car,
                                intencao, float(confianca), dados, None, municipio, None, _nota_correcao)

    if (
        intencao in _INTENT_FONTE_MAP
        and not cod_car
        and not municipio
        and _RANKING_RE.search(pergunta)
    ):
        fonte = _INTENT_FONTE_MAP[intencao]
        ranking = await buscar_ranking_municipios(fonte, limit=10)
        if ranking:
            label_map = {"deter": "alertas DETER", "prodes": "polígonos PRODES", "focos": "focos de queimada"}
            label = label_map[fonte]
            linhas = [f"  {i+1}. **{r['municipio']}** — {r['total']:,} {label}" for i, r in enumerate(ranking)]
            resposta_text = (
                f"Top {len(ranking)} municípios com mais **{label}** em SP:\n"
                + "\n".join(linhas)
            )
        else:
            resposta_text = "Não foi possível buscar o ranking. Tente novamente."
        resposta_text += _rodape_fonte(intencao)
        consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)
        return _montar_resposta(consulta_obj, pergunta, resposta_text, cod_car,
                                intencao, float(confianca), dados, None, municipio, None, _nota_correcao)

    # ── Coordenadas detectadas: busca propriedades próximas ──────────────────
    if coordenadas and not cod_car:
        lat, lon = coordenadas
        proximas = await buscar_propriedades_proximas(lat, lon, raio_m=5000, limit=5)
        if proximas:
            linhas = [_linha_prop(p, show_municipio=True) for p in proximas[:5]]
            resposta_text = (
                f"Encontrei **{len(proximas)} propriedade(s)** no raio de 5 km ao redor de "
                f"{lat:.5f}, {lon:.5f}:\n" + "\n".join(linhas)
                + "\n\nInforme o **código CAR** de uma delas para ver o relatório ASG completo."
            )
        else:
            resposta_text = (
                f"Nenhuma propriedade cadastrada no SICAR encontrada no raio de 5 km "
                f"ao redor de {lat:.5f}, {lon:.5f}. "
                "Verifique se as coordenadas pertencem a uma área rural cadastrada no SP."
            )
        resposta_text += _rodape_fonte(intencao)
        consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)
        return _montar_resposta(consulta_obj, pergunta, resposta_text, cod_car,
                                intencao, confianca, dados, acao, municipio, list(coordenadas), _nota_correcao)

    # CAR fornecido sem intenção explícita → relatório ASG completo como padrão
    if cod_car and not intencao:
        intencao = "relatorio"
        confianca = 0.75

    # ── Sem intenção ASG — tenta responder com contexto disponível ───────────
    if not intencao:
        if municipio:
            props = await buscar_propriedades_por_municipio(municipio, limit=10)
            if props:
                linhas = [_linha_prop(p) for p in props[:8]]
                total_label = f"{len(props)}+" if len(props) == 10 else str(len(props))
                resposta_text = (
                    f"Em **{municipio}**, encontrei **{total_label} propriedade(s)** rurais cadastradas no SICAR.\n\n"
                    + "\n\n".join(linhas)
                    + "\n\nInforme o **código CAR** de uma delas para análise ASG detalhada "
                    "(desmatamento, queimadas, alertas, áreas protegidas, governança...)."
                )
            else:
                resposta_text = (
                    f"Não encontrei propriedades cadastradas em **{municipio}** no banco local. "
                    "O município pode não ter dados no SICAR-SP ainda."
                )
        else:
            resposta_text = (
                "Não reconheci nenhuma intenção ou localidade nessa mensagem.\n\n"
                "Sou especializado em análises ASG de propriedades rurais de SP. Tente algo como:\n\n"
                "  • **Desmatamento** — *tem desmatamento PRODES nessa fazenda?*\n"
                "  • **Queimadas** — *houve foco de calor nessa área?*\n"
                "  • **Alertas DETER** — *tem alerta de degradação ativo?*\n"
                "  • **Terras Indígenas** — *tem sobreposição com TI?*\n"
                "  • **Unidades de Conservação** — *a área está em UC?*\n"
                "  • **Assentamentos / Quilombolas** — *tem assentamento INCRA aqui?*\n"
                "  • **Situação CAR** — *qual o status do cadastro ambiental rural?*\n"
                "  • **Relatório ASG** — *qual o risco ASG da propriedade?*\n"
                "  • **Município** — *queimadas em Campinas*\n"
                "  • **Coordenadas** — *-23.5, -46.6*"
            )
        consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)
        return _montar_resposta(consulta_obj, pergunta, resposta_text, cod_car,
                                None, 0.0, dados, acao, municipio, None, _nota_correcao)

    # ── Intenção detectada ────────────────────────────────────────────────────
    intent_meta = nlp_service.INTENTS.get(intencao, {})
    service_name = intent_meta.get("service")
    template = intent_meta.get("endpoint_template", "")

    _INTENCAO_LABELS = {
        "comunidades":  "assentamentos e quilombolas",
        "indigena":     "terras indígenas",
        "conservacao":  "unidades de conservação",
        "desmatamento": "desmatamento (PRODES)",
        "alerta":       "alertas DETER",
        "queimada":     "focos de queimada",
        "relatorio":    "relatório ASG",
        "governanca":   "governança / CAR",
        "fundiario":    "dados fundiários",
    }
    _INTENT_HINT = {
        "comunidades":  "verificar sobreposição com **assentamentos INCRA** e **territórios quilombolas**",
        "indigena":     "verificar sobreposição com **terras indígenas** (FUNAI)",
        "conservacao":  "verificar sobreposição com **unidades de conservação** (ICMBio)",
        "desmatamento": "consultar **histórico de desmatamento PRODES** da propriedade",
        "alerta":       "consultar **alertas DETER** de degradação ativa",
        "queimada":     "consultar **focos de queimada** (BDQueimadas/INPE)",
        "relatorio":    "gerar o **relatório ASG completo** com índice de risco",
    }

    if "{id}" in template:
        if not cod_car:
            intencao_label = _INTENCAO_LABELS.get(intencao, intencao.replace("_", " "))
            if municipio:
                acao = "zoom_municipio"
                if municipio_from_context:
                    resposta_text = (
                        f"Consultando **{intencao_label}** em **{municipio}** "
                        "— camada ativada no mapa."
                    )
                else:
                    props, mun_aggregate = await asyncio.gather(
                        buscar_propriedades_por_municipio(municipio, limit=8),
                        _buscar_stats_municipio(intencao, municipio),
                        return_exceptions=True,
                    )
                    if isinstance(props, Exception):
                        props = []
                    if isinstance(mun_aggregate, Exception):
                        mun_aggregate = None

                    if props:
                        linhas = [_linha_prop(p) for p in props[:6]]
                        total_label = f"{len(props)}+" if len(props) == 8 else str(len(props))
                        detail_hint = _INTENT_HINT.get(intencao, f"análise de {intencao_label}")

                        # Prefácio com dados agregados do município quando disponíveis
                        prefacio = _prefacio_municipio(intencao, municipio, mun_aggregate)

                        resposta_text = (
                            prefacio
                            + f"**{total_label} propriedade(s)** cadastradas em **{municipio}** (SICAR). "
                            f"Selecione uma para {detail_hint}:\n\n"
                            + "\n\n".join(linhas)
                            + f"\n\nInforme o **CAR** de uma delas para análise detalhada."
                        )
                    else:
                        resposta_text = (
                            f"Não encontrei propriedades cadastradas em **{municipio}** "
                            f"para consultar {intencao_label}."
                        )
                resposta_text += _rodape_fonte(intencao)
                consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)
                return _montar_resposta(consulta_obj, pergunta, resposta_text, cod_car,
                                        intencao, float(confianca), dados, acao, municipio, None, _nota_correcao)

            _camadas = {
                "queimada":     "**Queimadas** no painel do mapa",
                "desmatamento": "**PRODES** no painel do mapa",
                "alerta":       "**DETER** no painel do mapa",
                "indigena":     "**TI** no painel do mapa",
                "conservacao":  "**UC** no painel do mapa",
                "comunidades":  "**Assentamentos** e **Quilombolas** no painel do mapa",
            }
            camada_hint = _camadas.get(intencao)
            if camada_hint:
                resposta_text = (
                    f"Para ver **{intencao_label}** em todo o estado de SP, "
                    f"ative a camada {camada_hint} — ela mostra todos os registros.\n\n"
                    "Para análise em uma propriedade específica:\n"
                    "  • Mencione um **município** — ex: *queimadas em Campinas*\n"
                    "  • Ou informe o **código CAR** diretamente"
                )
            else:
                resposta_text = (
                    f"Para consultar **{intencao_label}** em uma propriedade específica, "
                    "informe o **código CAR** ou mencione um **município**."
                )
        else:
            path = template.format(id=cod_car)
            params = intent_meta.get("default_params") or {}

            if service_name == "relatorio_asg":
                dados = await obter_relatorio_car(cod_car)
            else:
                dados = await chamar_cruzamento(path, params=params)

            dados = await _enriquecer_dados(intencao, cod_car, dados)

            resposta_text = _formatar_resposta(intencao, cod_car, municipio, dados, path)
            acao = "zoom_propriedade"
    else:
        path = template
        params = intent_meta.get("default_params") or {}
        dados = await chamar_cruzamento(path, params=params)
        resposta_text = _formatar_resposta(intencao, cod_car, municipio, dados, path)

    resposta_text += _rodape_fonte(intencao)

    consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)
    return _montar_resposta(consulta_obj, pergunta, resposta_text, cod_car,
                            intencao, float(confianca), dados, acao, municipio, None, _nota_correcao)


# ── Formatação de linha de propriedade ───────────────────────────────────────

def _linha_prop(p: dict, show_municipio: bool = False) -> str:
    """**CAR** clickável sozinho na linha; detalhes na linha abaixo."""
    detalhes = []
    if p.get("area"):
        detalhes.append(f"{float(p['area']):.1f} ha")
    if p.get("status_imovel"):
        detalhes.append(p["status_imovel"])
    if show_municipio and p.get("municipio"):
        detalhes.append(p["municipio"])
    sub = f"\n  {' · '.join(detalhes)}" if detalhes else ""
    return f"**{p['cod_imovel']}**{sub}"


# ── Stats agregadas por município ────────────────────────────────────────────

_MUNICIPIO_FONTE_MAP = {
    "queimada":     "focos",
    "desmatamento": "prodes",
    "alerta":       "deter",
}

async def _buscar_stats_municipio(intencao: str, municipio: str) -> dict | None:
    fonte = _MUNICIPIO_FONTE_MAP.get(intencao)
    if not fonte:
        return None
    ranking = await buscar_ranking_municipios(fonte, limit=200)
    mun_norm = municipio.upper().strip()
    for r in ranking:
        if r.get("municipio", "").upper().strip() == mun_norm:
            return {"total": r["total"], "fonte": fonte}
    return None


def _prefacio_municipio(intencao: str, municipio: str, stats: dict | None) -> str:
    if not stats or not stats.get("total"):
        return ""
    total = stats["total"]
    _LABELS = {
        "focos":  ("foco(s) de queimada", "BDQueimadas/INPE"),
        "prodes": ("polígono(s) PRODES de desmatamento", "INPE"),
        "deter":  ("alerta(s) DETER de degradação", "INPE/DETER"),
    }
    label, fonte = _LABELS.get(stats["fonte"], (stats["fonte"], "INPE"))
    return f"Em **{municipio}**, há **{total} {label}** registrados ({fonte}).\n\n"


# ── Enriquecimento com dados do banco ────────────────────────────────────────

async def _enriquecer_dados(intencao: str, cod_car: str, dados_cruzamento) -> dict:
    if not cod_car:
        return dados_cruzamento or {}

    enriquecido = dict(dados_cruzamento) if isinstance(dados_cruzamento, dict) else {}

    try:
        tasks: dict[str, object] = {}
        if intencao in ("desmatamento", "queimada", "alerta", "relatorio"):
            tasks["_inpe_stats"] = buscar_stats_inpe_por_propriedade(cod_car)
        if intencao in ("indigena", "conservacao", "comunidades", "relatorio"):
            tasks["_areas_protegidas"] = buscar_areas_protegidas_por_propriedade(cod_car)
        if intencao in ("fundiario", "governanca", "relatorio"):
            tasks["_propriedade"] = buscar_por_car(cod_car)

        if tasks:
            keys = list(tasks.keys())
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(keys, results):
                if isinstance(result, Exception):
                    continue
                if result:
                    enriquecido[key] = result
    except Exception:
        pass

    return enriquecido


# ── Formatação de respostas por intenção ──────────────────────────────────────

def _formatar_resposta(
    intencao: str,
    cod_car: str | None,
    municipio: str | None,
    dados,
    endpoint_path: str,
) -> str:
    ref = f" para o imóvel **{cod_car}**" if cod_car else ""
    ref += f" ({municipio})" if municipio else ""

    if dados is None:
        return (
            f"Não foi possível obter dados{ref}. "
            "O serviço pode estar indisponível ou o CAR não foi encontrado no banco."
        )

    if isinstance(dados, dict) and "status_code" in dados and "_inpe_stats" not in dados:
        return (
            f"O serviço retornou erro HTTP {dados['status_code']}{ref}. "
            "Verifique se o código CAR existe no banco."
        )

    # ── Desmatamento / Queimada / Alerta ─────────────────────────────────────
    if intencao in ("desmatamento", "queimada", "alerta") and isinstance(dados, dict):
        stats = dados.get("_inpe_stats", {})

        if intencao == "desmatamento":
            n_pol = stats.get("prodes_poligonos", 0) if stats else 0
            area_ha = stats.get("prodes_area_ha", 0) if stats else 0
            if stats:
                if n_pol:
                    severity = "alto" if area_ha > 10 else "moderado" if area_ha > 2 else "baixo"
                    partes = [
                        f"A propriedade{ref} tem **{n_pol} polígono(s) PRODES** de desmatamento registrado(s).",
                        f"  • Área total desmatada: **{area_ha:.2f} ha** — impacto **{severity}**",
                        "  • Isso pode gerar **passivo ambiental** na Reserva Legal e APP.",
                        "  • Verifique o índice de risco ASG no painel à direita.",
                    ]
                    return "\n".join(partes)
                return (
                    f"Nenhum desmatamento PRODES encontrado dentro da propriedade{ref}. "
                    "A área apresenta **conformidade ambiental** nesse indicador."
                )

        if intencao == "queimada":
            focos = stats.get("focos", 0) if stats else 0
            if stats:
                if focos:
                    freq = "alta" if focos >= 10 else "moderada" if focos >= 3 else "baixa"
                    partes = [
                        f"Encontrei **{focos} foco(s) de calor** próximos à propriedade{ref}.",
                        f"  • Frequência: **{freq}** (dados BDQueimadas/INPE, raio de 10 km)",
                        "  • Focos recorrentes elevam o **índice de risco ASG** da propriedade.",
                    ]
                    return "\n".join(partes)
                return (
                    f"Nenhum foco de queimada encontrado no raio de 10 km da propriedade{ref}. "
                    "Indicador favorável no eixo ambiental."
                )

        if intencao == "alerta":
            deter = stats.get("deter", 0) if stats else 0
            if stats:
                if deter:
                    urgencia = "urgente" if deter >= 3 else "relevante"
                    partes = [
                        f"A propriedade{ref} tem **{deter} alerta(s) DETER** de degradação.",
                        f"  • Situação: **{urgencia}** — alertas indicam supressão vegetal recente.",
                        "  • Alertas DETER podem preceder registros PRODES formais.",
                        "  • Recomenda-se verificar o relatório ASG completo e o CAR atualizado.",
                    ]
                    return "\n".join(partes)
                return (
                    f"Nenhum alerta DETER de degradação ativa encontrado{ref}. "
                    "Situação **regular** nesse indicador."
                )

        # fallback sem stats (dados do cruzamento)
        total = dados.get("total_alertas", 0)
        passivos = dados.get("passivos", [])
        labels = {
            "desmatamento": "desmatamento (PRODES)",
            "queimada":     "focos de queimada (BDQueimadas)",
            "alerta":       "alertas de degradação (DETER)",
        }
        label = labels.get(intencao, intencao)
        if total == 0:
            return f"Nenhum registro de {label} encontrado{ref}."
        partes = [f"Encontrei **{total} registro(s)** de {label}{ref}:"]
        for p in passivos[:5]:
            fonte = p.get("fonte", "")
            data = str(p.get("data_referencia", ""))[:10]
            area = p.get("area_ha")
            linha = f"  • {fonte}"
            if data:
                linha += f" em {data}"
            if area and float(area) > 0:
                linha += f", **{float(area):.2f} ha**"
            partes.append(linha)
        if total > 5:
            partes.append(f"  … e mais {total - 5} registro(s).")
        return "\n".join(partes)

    # ── Indígena / Conservação / Comunidades ─────────────────────────────────
    if intencao in ("indigena", "conservacao", "comunidades") and isinstance(dados, dict):
        areas = dados.get("_areas_protegidas", {})

        if intencao == "indigena":
            tis = areas.get("ti", [])
            if not tis:
                return (
                    f"Nenhuma sobreposição com Terra Indígena encontrada{ref}. "
                    "Indicador **favorável** no eixo social ASG."
                )
            nomes = [t.get("nome") or t.get("cod_ti", "?") for t in tis]
            partes = [
                f"**Atenção:** A propriedade{ref} tem sobreposição com "
                f"**{len(tis)} Terra(s) Indígena(s)** (FUNAI):",
            ]
            partes.extend(f"  • {n}" for n in nomes)
            partes.append(
                "  ↳ Sobreposição com TI é **fator de risco ASG crítico** — "
                "pode impactar financiamento rural, certificações ambientais e licenciamentos."
            )
            return "\n".join(partes)

        if intencao == "conservacao":
            ucs = areas.get("uc", [])
            if not ucs:
                return (
                    f"Nenhuma sobreposição com Unidade de Conservação encontrada{ref}. "
                    "Indicador **favorável** no eixo social ASG."
                )
            nomes = [u.get("nome") or u.get("cod_uc", "?") for u in ucs]
            partes = [
                f"A propriedade{ref} tem sobreposição com "
                f"**{len(ucs)} Unidade(s) de Conservação (UC)**:",
            ]
            partes.extend(f"  • {n}" for n in nomes)
            partes.append(
                "  ↳ Sobreposição com UC exige **licenciamento específico** "
                "e pode restringir ampliação da área produtiva."
            )
            return "\n".join(partes)

        if intencao == "comunidades":
            assentamentos = areas.get("assentamento", [])
            quilombolas = areas.get("quilombola", [])

            if not assentamentos and not quilombolas:
                return (
                    f"Nenhuma sobreposição com assentamentos ou territórios quilombolas encontrada{ref}. "
                    "Indicador **favorável** no eixo social ASG."
                )

            partes = [f"Mapeei comunidades tradicionais sobrepostas à propriedade{ref}:"]

            if assentamentos:
                nomes_a = [a.get("nome") or a.get("cod_sipra", "?") for a in assentamentos]
                partes.append(f"\n**Assentamentos INCRA ({len(assentamentos)}):**")
                partes.extend(f"  • {n}" for n in nomes_a)
                partes.append(
                    "  ↳ Sobreposição com assentamento pode gerar **litígios fundiários** "
                    "e requer regularização junto ao INCRA."
                )

            if quilombolas:
                nomes_q = [q.get("nome") or q.get("cod_quilombola", "?") for q in quilombolas]
                partes.append(f"\n**Territórios Quilombolas ({len(quilombolas)}):**")
                partes.extend(f"  • {n}" for n in nomes_q)
                partes.append(
                    "  ↳ Territórios quilombolas têm **proteção constitucional** — "
                    "sobreposição é fator de **risco ASG elevado** e exige atenção jurídica."
                )

            return "\n".join(partes)

        # fallback indicadores ASG
        indicadores = dados.get("indicadores", [])
        cat_map = {"indigena": "Social", "conservacao": "Social", "comunidades": "Social"}
        cat = cat_map[intencao]
        relevantes = [i for i in indicadores if i.get("categoria") == cat]
        if not relevantes:
            return f"Nenhum indicador de '{cat}' encontrado{ref}."
        partes = [f"Indicadores de {cat}{ref}:"]
        for ind in relevantes:
            valor = ind.get("valor")
            unidade = ind.get("unidade", "")
            detalhe = ind.get("detalhe") or ""
            status = ind.get("status", "").upper()
            linha = f"  • {ind.get('nome')}: "
            linha += f"**{valor} {unidade}**".strip() if valor is not None else ""
            if detalhe:
                linha += f" ({detalhe})"
            linha += f" — {status}"
            partes.append(linha)
        return "\n".join(partes)

    # ── Governança ────────────────────────────────────────────────────────────
    if intencao == "governanca" and isinstance(dados, dict):
        prop = dados.get("_propriedade", {}) or {}
        status_raw = (prop.get("status_imovel") or prop.get("condicao") or "").upper()
        area = prop.get("area")
        municipio_prop = prop.get("municipio")

        _STATUS_MSG = {
            "AT": "CAR **ativo** — cadastro regular e em conformidade com o SICAR.",
            "PE": "CAR **pendente** — há declarações incorretas que precisam de correção no SICAR.",
            "SU": "CAR **suspenso** — operações podem estar restritas por decisão judicial ou administrativa.",
            "CA": "CAR **cancelado** — cadastro inválido. Risco fundiário **crítico**.",
        }
        status_msg = _STATUS_MSG.get(status_raw, f"Status CAR: **{status_raw or 'não informado'}**")

        partes = [f"Situação cadastral (SICAR){ref}:", f"  • {status_msg}"]
        if municipio_prop:
            partes.append(f"  • Município: **{municipio_prop}**/{prop.get('uf', 'SP')}")
        if area:
            partes.append(f"  • Área declarada: **{float(area):.2f} ha**")

        indicadores = dados.get("indicadores", [])
        gov_inds = [i for i in indicadores if i.get("categoria") == "Governança"]
        for ind in gov_inds[:3]:
            valor = ind.get("valor")
            detalhe = ind.get("detalhe") or ""
            linha = f"  • {ind.get('nome')}: "
            linha += f"**{valor}**" if valor is not None else detalhe or "—"
            partes.append(linha)

        return "\n".join(partes)

    # ── Fundiário ─────────────────────────────────────────────────────────────
    if intencao == "fundiario" and isinstance(dados, dict):
        prop = dados.get("_propriedade", {}) or {}
        area = prop.get("area")
        m_fiscal = prop.get("m_fiscal")
        municipio_prop = prop.get("municipio")

        partes = [f"Informações fundiárias{ref}:"]
        if municipio_prop:
            partes.append(f"  • Município: **{municipio_prop}**/{prop.get('uf', 'SP')}")
        if area:
            partes.append(f"  • Área total declarada: **{float(area):.2f} ha**")
        if m_fiscal:
            partes.append(f"  • Módulo fiscal: **{m_fiscal}** — referência para regularidade fundiária")

        tipo = prop.get("tipo_imovel")
        if tipo:
            partes.append(f"  • Tipo de imóvel: {tipo}")
        dat = prop.get("dat_criacao")
        if dat:
            partes.append(f"  • Data de criação CAR: {str(dat)[:10]}")

        indicadores = dados.get("indicadores", [])
        fund_inds = [i for i in indicadores if "fiscal" in str(i.get("nome", "")).lower()
                     or "area" in str(i.get("nome", "")).lower()]
        for ind in fund_inds[:3]:
            valor = ind.get("valor")
            detalhe = ind.get("detalhe") or ""
            linha = f"  • {ind.get('nome')}: "
            linha += f"**{valor}**" if valor is not None else detalhe or "—"
            partes.append(linha)

        if len(partes) == 1:
            return f"Não encontrei dados fundiários detalhados{ref}. Verifique se o CAR está cadastrado no SICAR."
        return "\n".join(partes)

    # ── Relatório consolidado ─────────────────────────────────────────────────
    if intencao == "relatorio" and isinstance(dados, dict):
        resumo = dados.get("resumo_asg", {})
        score = resumo.get("indice_risco", 0)
        nivel = resumo.get("nivel", "desconhecido")
        prop_dados = (dados.get("propriedade") or {}).get("dados") or {}
        mun = prop_dados.get("municipio") or municipio
        ref2 = f" ({mun})" if mun else ref

        _NIVEL_MSG = {
            "baixo": f"**Risco baixo ({score:.0f}/100)** — boa conformidade ambiental e fundiária.",
            "medio": f"**Risco moderado ({score:.0f}/100)** — há pendências que merecem atenção.",
            "alto":  f"**Risco alto ({score:.0f}/100)** — sobreposições ou passivos ambientais relevantes identificados.",
        }
        nivel_msg = _NIVEL_MSG.get(nivel, f"Índice de risco: **{score:.0f}/100** ({nivel})")

        stats = dados.get("_inpe_stats", {})
        areas = dados.get("_areas_protegidas", {})

        partes = [f"Relatório ASG{ref2}:", f"  • {nivel_msg}"]

        if stats:
            prodes_ha = stats.get("prodes_area_ha", 0)
            focos = stats.get("focos", 0)
            deter = stats.get("deter", 0)
            if prodes_ha:
                partes.append(f"  • Desmatamento PRODES: **{prodes_ha:.2f} ha**")
            if deter:
                partes.append(f"  • Alertas DETER: **{deter}** (degradação ativa)")
            if focos:
                partes.append(f"  • Focos de queimada: **{focos}** (raio 10 km)")

        if areas:
            n_ti  = len(areas.get("ti", []))
            n_uc  = len(areas.get("uc", []))
            n_ass = len(areas.get("assentamento", []))
            n_qui = len(areas.get("quilombola", []))
            if n_ti:
                partes.append(f"  • Terras Indígenas sobrepostas: **{n_ti}** ⚠")
            if n_uc:
                partes.append(f"  • Unidades de Conservação sobrepostas: **{n_uc}**")
            if n_ass:
                partes.append(f"  • Assentamentos INCRA sobrepostos: **{n_ass}**")
            if n_qui:
                partes.append(f"  • Territórios Quilombolas sobrepostos: **{n_qui}**")

        partes.append("\nConsulte o **painel de relatório ASG** à direita para todos os indicadores detalhados.")
        return "\n".join(partes)

    return f"Dados disponíveis{ref}. Consulte o painel de relatório para detalhes."


# ── Rodapé de fonte ───────────────────────────────────────────────────────────

def _rodape_fonte(intencao: str | None) -> str:
    if not intencao:
        return ""
    fonte = nlp_service.INTENT_FONTES.get(intencao)
    if not fonte:
        return ""
    return f"\n\n📌 Fonte: {fonte}"


# ── Montagem da resposta final ────────────────────────────────────────────────

def _montar_resposta(
    consulta_obj,
    pergunta: str,
    resposta_text: str,
    cod_car: str | None,
    intencao: str | None,
    confianca: float,
    dados,
    acao: str | None,
    municipio: str | None,
    coordenadas: list | None,
    correcao: str = "",
) -> dict:
    return {
        "id": consulta_obj.id,
        "pergunta": pergunta,
        "resposta": correcao + resposta_text,
        "cod_car": cod_car,
        "cod_imovel": cod_car,
        "criado_em": consulta_obj.criado_em,
        "intencao_detectada": intencao,
        "confianca": confianca,
        "dados": dados if isinstance(dados, dict) else None,
        "acao": acao,
        "municipio_detectado": municipio,
        "coordenadas_detectadas": coordenadas,
    }


def listar_consultas(db: Session):
    return service.listar_consultas(db)
