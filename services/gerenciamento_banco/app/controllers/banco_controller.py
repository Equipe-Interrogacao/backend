from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.services.banco_service import BancoService

service = BancoService()


def listar_propriedades(db: Session):
    return service.listar_propriedades(db)


def buscar_propriedade(id: int, db: Session):
    propriedade = service.buscar_por_id(db, id)
    if not propriedade:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return propriedade


def criar_propriedade(dados: dict, db: Session):
    return service.criar_propriedade(db, dados)


def deletar_propriedade(id: int, db: Session):
    propriedade = service.deletar_propriedade(db, id)
    if not propriedade:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return {"mensagem": f"Propriedade {id} deletada com sucesso"}
