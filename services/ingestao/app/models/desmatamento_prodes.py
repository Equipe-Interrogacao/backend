from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class DesmatamentoProdes(Base):
    """
    Polígonos anuais de desmatamento do PRODES (TerraBrasilis / INPE).

    Fonte: https://terrabrasilis.dpi.inpe.br (WFS GeoServer)
    Bioma de referência para SP: Cerrado e Mata Atlântica.
    Upsert idempotente por id_poligono.
    """
    __tablename__ = "desmatamento_prodes"

    id = Column(Integer, primary_key=True, index=True)

    # Identificador estável vindo do TerraBrasilis (e.g. "prodes_cerrado_nb.123")
    id_poligono = Column(String, unique=True, index=True, nullable=False)

    ano = Column(Integer, index=True)              # Ano de referência do PRODES
    area_km2 = Column(Float)                       # Área desmatada em km²
    classname = Column(String)                     # Classe (ex.: "d" para desmatamento)

    estado = Column(String)                        # Nome completo do estado
    uf = Column(String, default="SP", index=True)  # Sigla — sempre filtrada para SP
    municipio = Column(String, index=True)
    bioma = Column(String, index=True)             # Ex.: "Cerrado", "Mata Atlântica"

    # Geometria MULTIPOLYGON WGS84 (SRID 4326)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))

    # Controle interno
    ingerido_em = Column(DateTime, server_default=func.now())
