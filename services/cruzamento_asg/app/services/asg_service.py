from sqlalchemy.orm import Session
from app.models.analise_asg import AnaliseASG


class ASGService:

    def buscar_analise_por_car(self, db: Session, cod_car: str):
        return db.query(AnaliseASG).filter(AnaliseASG.cod_car == cod_car).first()

    def listar_analises(self, db: Session):
        return db.query(AnaliseASG).all()

    def criar_analise(self, db: Session, dados: dict):
        analise = AnaliseASG(**dados)
        db.add(analise)
        db.commit()
        db.refresh(analise)
        return analise
