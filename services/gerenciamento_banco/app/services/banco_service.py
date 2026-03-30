from sqlalchemy.orm import Session
from app.models.propriedade import Propriedade


class BancoService:

    def listar_propriedades(self, db: Session):
        return db.query(Propriedade).all()

    def buscar_por_id(self, db: Session, id: int):
        return db.query(Propriedade).filter(Propriedade.id == id).first()

    def criar_propriedade(self, db: Session, dados: dict):
        propriedade = Propriedade(**dados)
        db.add(propriedade)
        db.commit()
        db.refresh(propriedade)
        return propriedade

    def deletar_propriedade(self, db: Session, id: int):
        propriedade = self.buscar_por_id(db, id)
        if propriedade:
            db.delete(propriedade)
            db.commit()
        return propriedade
