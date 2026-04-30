from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class TerraIndigena(Base):
    """
    Terras Indígenas (FUNAI).

    Fonte: https://geoserver.funai.gov.br/geoserver/Funai/ows (WFS)
    Layer: Funai:tis_poligonais
    Filtrado por uf_sigla contendo 'SP'.
    Upsert idempotente por cod_ti.
    """
    __tablename__ = "terra_indigena"

    id = Column(Integer, primary_key=True, index=True)

    cod_ti = Column(String, unique=True, index=True, nullable=False)  # terrai_cod
    nome = Column(String, index=True)        # terrai_nom
    etnia = Column(String, index=True)       # etnia_nome
    fase = Column(String, index=True)        # Declarada, Delimitada, Demarcada, Homologada, Regularizada
    uf = Column(String, index=True)          # uf_sigla
    area_ha = Column(Float)

    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))

    ingerido_em = Column(DateTime, server_default=func.now())
