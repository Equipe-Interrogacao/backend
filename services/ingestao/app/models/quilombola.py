from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class Quilombola(Base):
    """
    Territórios Quilombolas (FCP / INCRA).

    Fonte: INCRA WFS (territórios com geometria homologada/regularizada)
    https://acervofundiario.incra.gov.br/i3geo/ogc.php
    Filtrado por sg_uf='SP'.
    Upsert idempotente por cod_quilombola (nr_processo).
    """
    __tablename__ = "quilombola"

    id = Column(Integer, primary_key=True, index=True)

    cod_quilombola = Column(String, unique=True, index=True, nullable=False)  # nr_processo
    nome = Column(String, index=True)          # nm_comunidade
    etnia = Column(String)                     # nm_etnia
    municipio = Column(String, index=True)     # nm_municipio
    uf = Column(String, index=True)            # sg_uf
    area_ha = Column(Float)
    fase = Column(String)                      # fase de regularização fundiária
    dt_publicacao = Column(DateTime)

    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))

    ingerido_em = Column(DateTime, server_default=func.now())
