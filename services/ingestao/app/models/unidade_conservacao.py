from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class UnidadeConservacao(Base):
    """
    Unidades de Conservação federais (ICMBio / CNUC).

    Fonte: https://www.icmbio.gov.br/geoserver/SMCUC/ows (WFS)
    Filtrado por siglaUF contendo 'SP'.
    Upsert idempotente por cod_uc (codigoCnuc).
    """
    __tablename__ = "unidade_conservacao"

    id = Column(Integer, primary_key=True, index=True)

    cod_uc = Column(String, unique=True, index=True, nullable=False)  # codigoCnuc
    nome = Column(String, index=True)
    categoria = Column(String, index=True)   # Parque Nacional, APA, RESEX, ESEC…
    grupo = Column(String, index=True)       # Proteção Integral / Uso Sustentável
    esfera = Column(String)                  # Federal, Estadual, Municipal
    uf = Column(String, index=True)          # siglaUF (pode conter múltiplas)
    area_ha = Column(Float)

    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))

    ingerido_em = Column(DateTime, server_default=func.now())
