from sqlalchemy.orm import Session
from app.models.propriedade import Propriedade


class IngestaoService:

    def buscar_por_car(self, db: Session, cod_car: str):
        return db.query(Propriedade).filter(Propriedade.cod_car == cod_car).first()

    def listar_propriedades(self, db: Session):
        return db.query(Propriedade).all()

    def criar_propriedade(self, db: Session, dados: dict):
        propriedade = Propriedade(**dados)
        db.add(propriedade)
        db.commit()
        db.refresh(propriedade)
        return propriedade
