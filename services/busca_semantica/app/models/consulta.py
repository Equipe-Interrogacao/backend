from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.config.database import Base


class Consulta(Base):
    __tablename__ = "consultas"

    id = Column(Integer, primary_key=True, index=True)
    pergunta = Column(Text, nullable=False)
    resposta = Column(Text)
    cod_car = Column(String, index=True)
    criado_em = Column(DateTime, server_default=func.now())
