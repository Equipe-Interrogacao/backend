from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.services.ingestao_service import IngestaoService

service = IngestaoService()


def buscar_propriedade(cod_car: str, db: Session):
    propriedade = service.buscar_por_car(db, cod_car)
    if not propriedade:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return propriedade


def listar_propriedades(db: Session):
    return service.listar_propriedades(db)


def criar_propriedade(dados: dict, db: Session):
    return service.criar_propriedade(db, dados)
