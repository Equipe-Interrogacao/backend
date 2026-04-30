from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class UnidadeConservacao(Base):
    __tablename__ = "unidade_conservacao"

    id = Column(Integer, primary_key=True, index=True)
    cod_uc = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, index=True)
    categoria = Column(String, index=True)
    grupo = Column(String, index=True)
    esfera = Column(String)
    uf = Column(String, index=True)
    area_ha = Column(Float)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))
    ingerido_em = Column(DateTime, server_default=func.now())


class TerraIndigena(Base):
    __tablename__ = "terra_indigena"

    id = Column(Integer, primary_key=True, index=True)
    cod_ti = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, index=True)
    etnia = Column(String)
    fase = Column(String)
    uf = Column(String, index=True)
    area_ha = Column(Float)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))
    ingerido_em = Column(DateTime, server_default=func.now())


class Assentamento(Base):
    __tablename__ = "assentamento"

    id = Column(Integer, primary_key=True, index=True)
    cod_sipra = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, index=True)
    tipo = Column(String)
    municipio = Column(String, index=True)
    uf = Column(String, index=True)
    area_ha = Column(Float)
    familias = Column(Integer)
    dt_criacao = Column(DateTime)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))
    ingerido_em = Column(DateTime, server_default=func.now())


class Quilombola(Base):
    __tablename__ = "quilombola"

    id = Column(Integer, primary_key=True, index=True)
    cod_quilombola = Column(String, unique=True, index=True, nullable=False)
    nome = Column(String, index=True)
    etnia = Column(String)
    municipio = Column(String, index=True)
    uf = Column(String, index=True)
    area_ha = Column(Float)
    fase = Column(String)
    dt_publicacao = Column(DateTime)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))
    ingerido_em = Column(DateTime, server_default=func.now())
