from sqlalchemy.orm import Session

from app.services.busca_service import BuscaService
from app.schemas.consulta_schema import ConsultaCreate
from app.services import nlp_service
from app.clients.cruzamento_client import chamar_cruzamento
from app.clients.relatorio_client import obter_relatorio_car

service = BuscaService()


async def realizar_consulta(payload: ConsultaCreate, db: Session):
    pergunta = payload.pergunta
    cod_car = payload.cod_car or nlp_service.extrair_cod_imovel(pergunta)

    intencao, confianca, matches = nlp_service.extrair_intencao(pergunta)
    municipio = nlp_service.extrair_municipio(pergunta)

    resposta_text = ""
    dados = None

    if not intencao:
        docs = nlp_service.obter_intencoes_documentacao()
        exemplos = ", ".join(
            f"'{v['palavras_chave'][0]}'" for v in docs.values() if v.get("palavras_chave")
        )
        resposta_text = (
            "Não consegui identificar a intenção da sua pergunta. "
            f"Tente usar palavras como: {exemplos}. "
            "Consulte GET /busca/intencoes para a lista completa."
        )
    else:
        intent_meta = nlp_service.INTENTS.get(intencao, {})
        service_name = intent_meta.get("service")
        template = intent_meta.get("endpoint_template", "")

        if "{id}" in template:
            if not cod_car:
                resposta_text = (
                    f"Intenção '{intencao}' detectada, mas não encontrei um código CAR na pergunta. "
                    "Inclua o CAR no campo `cod_imovel` ou escreva-o na pergunta."
                )
            else:
                path = template.format(id=cod_car)
                params = intent_meta.get("default_params") or {}
                if service_name == "relatorio_asg":
                    dados = await obter_relatorio_car(cod_car)
                else:
                    dados = await chamar_cruzamento(path, params=params)
                resposta_text = _formatar_resposta(intencao, cod_car, municipio, dados, path)
        else:
            path = template
            params = intent_meta.get("default_params") or {}
            dados = await chamar_cruzamento(path, params=params)
            resposta_text = _formatar_resposta(intencao, cod_car, municipio, dados, path)

    consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)

    return {
        "id": consulta_obj.id,
        "pergunta": pergunta,
        "resposta": resposta_text,
        "cod_car": cod_car,
        "cod_imovel": cod_car,
        "criado_em": consulta_obj.criado_em,
        "intencao_detectada": intencao,
        "confianca": float(confianca),
        "dados": dados,
    }


def _formatar_resposta(
    intencao: str,
    cod_car: str | None,
    municipio: str | None,
    dados: dict | list | None,
    endpoint_path: str,
) -> str:
    ref = f" para o imóvel {cod_car}" if cod_car else ""
    ref += f" ({municipio})" if municipio else ""

    if dados is None:
        return (
            f"Não foi possível obter dados{ref}. "
            "O serviço pode estar indisponível ou o CAR não foi encontrado."
        )

    if isinstance(dados, dict) and "status_code" in dados:
        return (
            f"O serviço retornou erro HTTP {dados['status_code']}{ref}. "
            "Verifique se o código CAR existe no banco."
        )

    # Passivos ambientais — desmatamento / queimada / alerta
    if intencao in ("desmatamento", "queimada", "alerta") and isinstance(dados, dict):
        total = dados.get("total_alertas", 0)
        passivos = dados.get("passivos", [])
        labels = {
            "desmatamento": "desmatamento (PRODES)",
            "queimada": "focos de queimada",
            "alerta": "alertas DETER",
        }
        if total == 0:
            return f"Nenhum registro de {labels.get(intencao, intencao)} encontrado{ref}."
        partes = [f"Encontrei {total} registro(s) de {labels.get(intencao, intencao)}{ref}:"]
        for p in passivos[:5]:
            fonte = p.get("fonte", "")
            data = str(p.get("data_referencia", ""))[:10]
            area = p.get("area_ha")
            linha = f"  • {fonte}"
            if data:
                linha += f" em {data}"
            if area and float(area) > 0:
                linha += f", {float(area):.2f} ha"
            partes.append(linha)
        if total > 5:
            partes.append(f"  … e mais {total - 5} registro(s).")
        return "\n".join(partes)

    # Indicadores ASG (Task 10) — indigena / conservacao / governanca
    if intencao in ("indigena", "conservacao", "governanca") and isinstance(dados, dict):
        indicadores = dados.get("indicadores", [])
        cat_map = {"indigena": "Social", "conservacao": "Social", "governanca": "Governança"}
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
            linha += f"{valor} {unidade}".strip() if valor is not None else ""
            if detalhe:
                linha += f" ({detalhe})"
            linha += f" — {status}"
            partes.append(linha)
        return "\n".join(partes)

    # Relatório consolidado Task 9
    if intencao == "relatorio" and isinstance(dados, dict):
        resumo = dados.get("resumo_asg", {})
        score = resumo.get("indice_risco", 0)
        nivel = resumo.get("nivel", "desconhecido")
        prop_dados = (dados.get("propriedade") or {}).get("dados") or {}
        mun = prop_dados.get("municipio")
        ref2 = f" ({mun})" if mun else ref
        return (
            f"Relatório ASG{ref2}: índice de risco {score:.0f}/100 — nível {nivel}. "
            "Dados disponíveis nas seções: desmatamento, queimadas e áreas protegidas."
        )

    return f"Dados retornados pelo serviço{ref}. Consulte o campo `dados` na resposta JSON."


def listar_consultas(db: Session):
    return service.listar_consultas(db)
