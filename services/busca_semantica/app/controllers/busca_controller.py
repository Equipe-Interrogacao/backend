from sqlalchemy.orm import Session
from app.services.busca_service import BuscaService
from app.schemas.consulta_schema import ConsultaCreate

service = BuscaService()


async def realizar_consulta(payload: ConsultaCreate, db: Session):
    resposta = await _gerar_resposta(payload.pergunta, payload.cod_car)
    return service.registrar_consulta(db, payload.pergunta, resposta, payload.cod_car)


async def _gerar_resposta(pergunta: str, cod_car: str | None) -> str:
    if not cod_car:
        return (
            f"Pergunta recebida: '{pergunta}'. "
            "Informe um código CAR para consultas sobre uma propriedade específica."
        )

    from app.clients.gerenciamento_banco_client import (
        buscar_por_car,
        buscar_stats_inpe_por_propriedade,
    )
    propriedade = await buscar_por_car(cod_car)

    if not propriedade:
        return (
            f"Não encontrei a propriedade '{cod_car}' no banco de dados. "
            "Verifique se o código CAR está correto e se os dados foram ingeridos."
        )

    municipio = propriedade.get("municipio") or "município não informado"
    uf = propriedade.get("uf") or "SP"
    area = propriedade.get("area")
    status = propriedade.get("status_imovel") or "status desconhecido"

    area_info = f", área de {area:.2f} ha" if area else ""

    # Dados INPE espacialmente sobrepostos à propriedade (não ao município)
    inpe = await buscar_stats_inpe_por_propriedade(cod_car)

    partes = [
        f"Propriedade {cod_car} localizada em {municipio}/{uf}{area_info}.",
        f"Status CAR: {status}.",
    ]

    if inpe["prodes_area_ha"] > 0:
        partes.append(
            f"Desmatamento PRODES DENTRO da propriedade: {inpe['prodes_poligonos']} polígono(s), "
            f"área real de {inpe['prodes_area_ha']} ha."
        )
    if inpe["deter"] > 0:
        partes.append(
            f"Alertas DETER sobrepostos à propriedade: {inpe['deter']} alerta(s)."
        )
    if inpe["focos"] > 0:
        partes.append(
            f"Focos de queimada dentro da propriedade: "
            f"{inpe['focos']} foco(s) detectado(s) (2016–2025)."
        )
    if inpe["prodes_area_ha"] == 0 and inpe["deter"] == 0 and inpe["focos"] == 0:
        partes.append(
            "Nenhuma sobreposição INPE (PRODES/DETER/Queimadas) encontrada para esta propriedade."
        )

    partes.append(f"Pergunta registrada: {pergunta}")
    return " ".join(partes)


def listar_consultas(db: Session):
    return service.listar_consultas(db)
