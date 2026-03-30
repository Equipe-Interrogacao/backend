from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.services.asg_service import ASGService

service = ASGService()


def buscar_analise(cod_car: str, db: Session):
    analise = service.buscar_analise_por_car(db, cod_car)
    if not analise:
        raise HTTPException(status_code=404, detail="Análise ASG não encontrada para este CAR")
    return analise


def listar_analises(db: Session):
    return service.listar_analises(db)


def criar_analise(dados: dict, db: Session):
    return service.criar_analise(db, dados)
