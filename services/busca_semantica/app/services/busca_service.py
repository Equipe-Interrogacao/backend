from sqlalchemy.orm import Session
from app.models.consulta import Consulta


class BuscaService:

    def registrar_consulta(self, db: Session, pergunta: str, resposta: str, cod_car: str = None):
        consulta = Consulta(pergunta=pergunta, resposta=resposta, cod_car=cod_car)
        db.add(consulta)
        db.commit()
        db.refresh(consulta)
        return consulta

    def listar_consultas(self, db: Session):
        return db.query(Consulta).order_by(Consulta.id.desc()).all()
