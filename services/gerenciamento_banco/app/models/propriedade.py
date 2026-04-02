from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class Propriedade(Base):
    __tablename__ = "propriedades"

    id = Column(Integer, primary_key=True, index=True)

    # Campos reais do GeoServer CAR (sicar:sicar_imoveis_{uf})
    cod_imovel = Column(String, unique=True, index=True, nullable=False)
    status_imovel = Column(String, index=True)       # ex: "AT", "PE", "CA", "SU"
    dat_criacao = Column(DateTime)
    area = Column(Float)                              # Área em hectares
    condicao = Column(String)                         # ex: "Aguardando análise"
    uf = Column(String, default="SP", index=True)     # Sigla do estado
    municipio = Column(String, index=True)
    cod_municipio_ibge = Column(String)
    m_fiscal = Column(String)
    tipo_imovel = Column(String)                      # ex: "IRU", "POL"

    # Geometria MULTIPOLYGON WGS84 (SRID 4326)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))

    # Controle interno
    ingerido_em = Column(DateTime, server_default=func.now())
