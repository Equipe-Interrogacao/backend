from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class Assentamento(Base):
    """
    Projetos de Assentamento (INCRA).

    Fonte: https://acervofundiario.incra.gov.br/i3geo/ogc.php (WFS)
    Filtrado por sg_uf='SP'.
    Upsert idempotente por cod_sipra (cd_sipra).
    """
    __tablename__ = "assentamento"

    id = Column(Integer, primary_key=True, index=True)

    cod_sipra = Column(String, unique=True, index=True, nullable=False)  # cd_sipra
    nome = Column(String, index=True)         # no_projeto
    tipo = Column(String)                     # tp_assentamento
    municipio = Column(String, index=True)    # no_municipio
    uf = Column(String, index=True)           # sg_uf
    area_ha = Column(Float)                   # area_ha
    familias = Column(Integer)                # qt_familias_assentadas
    dt_criacao = Column(DateTime)

    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))

    ingerido_em = Column(DateTime, server_default=func.now())
