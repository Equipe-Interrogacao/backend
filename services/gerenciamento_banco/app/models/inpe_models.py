from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class DesmatamentoProdes(Base):
    __tablename__ = "desmatamento_prodes"

    id = Column(Integer, primary_key=True, index=True)
    id_poligono = Column(String, unique=True, index=True, nullable=False)
    ano = Column(Integer, index=True)
    area_km2 = Column(Float)
    classname = Column(String)
    estado = Column(String)
    uf = Column(String, default="SP", index=True)
    municipio = Column(String, index=True)
    bioma = Column(String, index=True)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))
    ingerido_em = Column(DateTime, server_default=func.now())


class AlertaDeter(Base):
    __tablename__ = "alerta_deter"

    id = Column(Integer, primary_key=True, index=True)
    id_alerta = Column(String, unique=True, index=True, nullable=False)
    classname = Column(String, index=True)
    view_date = Column(DateTime, index=True)
    area_km2 = Column(Float)
    uc = Column(String)
    uf = Column(String, default="SP", index=True)
    municipio = Column(String, index=True)
    bioma = Column(String)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))
    ingerido_em = Column(DateTime, server_default=func.now())


class FocoQueimada(Base):
    __tablename__ = "foco_queimada"

    id = Column(Integer, primary_key=True, index=True)
    id_foco = Column(String, unique=True, index=True, nullable=False)
    data_hora_gmt = Column(DateTime, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    satelite = Column(String)
    municipio = Column(String, index=True)
    estado = Column(String, default="SP", index=True)
    pais = Column(String)
    bioma = Column(String, index=True)
    frp = Column(Float)
    geometria = Column(Geometry("POINT", srid=4326))
    ingerido_em = Column(DateTime, server_default=func.now())
