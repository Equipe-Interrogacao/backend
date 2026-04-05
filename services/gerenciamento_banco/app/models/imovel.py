from sqlalchemy import Column, DateTime, Float, Integer, String
from geoalchemy2 import Geometry
from app.config.database import Base


class Imovel(Base):
    """
    Imóvel rural cadastrado (PostGIS).
    Tabela alinhada à consulta por código CAR (SCRUM-3).
    """

    __tablename__ = "imovel"

    id = Column(Integer, primary_key=True, index=True)
    codigo_car = Column(String(80), unique=True, index=True, nullable=False)
    area_ha = Column(Float, nullable=True)
    municipio = Column(String(255), nullable=True)
    situacao = Column(String(128), nullable=True)
    dt_inscricao = Column(DateTime(timezone=True), nullable=True)
    dt_analise = Column(DateTime(timezone=True), nullable=True)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
