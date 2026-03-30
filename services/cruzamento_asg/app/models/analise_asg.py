from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.config.database import Base


class AnaliseASG(Base):
    __tablename__ = "analises_asg"

    id = Column(Integer, primary_key=True, index=True)
    cod_car = Column(String, index=True, nullable=False)
    area_desmatada_ha = Column(Float, default=0)
    deficit_app_ha = Column(Float, default=0)
    deficit_reserva_legal_ha = Column(Float, default=0)
    sobreposicao_uc = Column(String)
    sobreposicao_ti = Column(String)
    criado_em = Column(DateTime, server_default=func.now())
