from sqlalchemy.orm import Session
from app.services.busca_service import BuscaService
from app.schemas.consulta_schema import ConsultaCreate

from app.services import nlp_service
from app.clients.gerenciamento_banco_client import buscar_por_car
from app.clients.cruzamento_client import chamar_cruzamento
from app.clients.relatorio_client import obter_relatorio_car

service = BuscaService()


async def realizar_consulta(payload: ConsultaCreate, db: Session):
    pergunta = payload.pergunta
    # extraction: prefer provided cod_car, else attempt from text
    cod_car = payload.cod_car or nlp_service.extrair_cod_imovel(pergunta)

    intencao, confianca, matches = nlp_service.extrair_intencao(pergunta)
    municipio = nlp_service.extrair_municipio(pergunta)

    resposta_text = ""
    dados = None

    if not intencao:
        # fallback: list supported intents
        docs = nlp_service.obter_intencoes_documentacao()
        resposta_text = (
            "Não consegui identificar a intenção da sua pergunta. "
            "Perguntas suportadas (exemplos de palavras-chave): "
            f"{', '.join([k for k in docs.keys()])}"
        )
    else:
        # route to microservice
        intent_meta = nlp_service.INTENTS.get(intencao, {})
        service_name = intent_meta.get("service")

        # If intent requires CAR id, prefer cod_car
        if "{id}" in intent_meta.get("endpoint_template", ""):
            if not cod_car:
                resposta_text = (
                    f"Intenção '{intencao}' detectada (palavras: {matches}), mas não foi encontrado código CAR. "
                    "Forneça um `cod_car` no payload ou inclua o CAR na pergunta."
                )
            else:
                path = intent_meta["endpoint_template"].format(id=cod_car)
                params = intent_meta.get("default_params", {})
                if service_name == "cruzamento_asg":
                    dados = await chamar_cruzamento(path, params=params)
                elif service_name == "relatorio_asg":
                    dados = await obter_relatorio_car(cod_car)
                resposta_text = formatar_resposta_humanizada(intencao, cod_car, municipio, dados, service_name, path)
        else:
            # endpoints that don't need id
            path = intent_meta.get("endpoint_template", "")
            params = intent_meta.get("default_params", {})
            if service_name == "cruzamento_asg":
                dados = await chamar_cruzamento(path, params=params)
            resposta_text = formatar_resposta_humanizada(intencao, cod_car, municipio, dados, service_name, path)

    # Persist consulta (store textual resposta summary)
    consulta_obj = service.registrar_consulta(db, pergunta, resposta_text, cod_car)

    # Build API response including detected intent and confidence
    result = {
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
    return result


def formatar_resposta_humanizada(
    intencao: str | None,
    cod_car: str | None,
    municipio: str | None,
    dados: dict | None,
    service_name: str | None = None,
    endpoint_path: str | None = None,
) -> str:
    if not intencao:
        return "Intenção não identificada."

    phr = f"Intenção detectada: {intencao}."
    if cod_car:
        phr += f" Código CAR: {cod_car}."
    if municipio:
        phr += f" Município mencionado: {municipio}."
    if dados is None:
        if service_name and endpoint_path:
            phr += (
                f" Não consegui obter dados do microsserviço '{service_name}' em '{endpoint_path}'. "
                "O serviço pode estar indisponível ou inacessível neste ambiente."
            )
        else:
            phr += " Nenhum dado retornado pelo microsserviço."
    elif isinstance(dados, dict) and "status_code" in dados:
        status_code = dados.get("status_code")
        if service_name and endpoint_path:
            phr += (
                f" O microsserviço '{service_name}' respondeu com erro HTTP {status_code} em '{endpoint_path}'. "
                "Consulte os logs do serviço alvo para mais detalhes."
            )
        else:
            phr += f" O microsserviço respondeu com erro HTTP {status_code}."
    else:
        # Summarize a bit
        try:
            if isinstance(dados, dict) and "total" in dados:
                phr += f" Resultado: {dados.get('total')} itens encontrados."
            else:
                phr += " Dados retornados pelo microsserviço anexados na resposta." 
        except Exception:
            phr += " Dados retornados pelo microsserviço anexados na resposta."

    return phr


def listar_consultas(db: Session):
    return service.listar_consultas(db)
