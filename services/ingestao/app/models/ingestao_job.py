from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.config.database import Base


class IngestaoJob(Base):
    __tablename__ = "ingestao_jobs"

    id = Column(Integer, primary_key=True)
    estado = Column(String, unique=True, index=True, nullable=False)
    ultimo_start_index = Column(Integer, default=0)   # última página salva com sucesso
    total_salvos = Column(Integer, default=0)
    total_ignorados = Column(Integer, default=0)
    status = Column(String, default="rodando")        # rodando | concluido | falhou
    iniciado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())
    erro = Column(String)
