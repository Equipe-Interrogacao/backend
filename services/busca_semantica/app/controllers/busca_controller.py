from sqlalchemy.orm import Session
from app.services.busca_service import BuscaService
from app.schemas.consulta_schema import ConsultaCreate

service = BuscaService()


def realizar_consulta(payload: ConsultaCreate, db: Session):
    resposta = f"Resposta gerada para: {payload.pergunta}"
    return service.registrar_consulta(db, payload.pergunta, resposta, payload.cod_car)


def listar_consultas(db: Session):
    return service.listar_consultas(db)
