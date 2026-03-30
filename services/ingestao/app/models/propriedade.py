from sqlalchemy import Column, Integer, String, Float, DateTime
from geoalchemy2 import Geometry
from app.config.database import Base


class Propriedade(Base):
    __tablename__ = "propriedades"

    id = Column(Integer, primary_key=True, index=True)
    cod_car = Column(String, unique=True, index=True, nullable=False)
    nome_proprietario = Column(String)
    municipio = Column(String)
    estado = Column(String, default="SP")
    area_total_ha = Column(Float)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))
