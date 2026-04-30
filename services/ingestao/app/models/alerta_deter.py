from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class AlertaDeter(Base):
    """
    Alertas em tempo-real de desmatamento do DETER (TerraBrasilis / INPE).

    Fonte: https://terrabrasilis.dpi.inpe.br (WFS GeoServer, workspace deter-cerrado)
    Filtrado por uf='SP'.
    Upsert idempotente por id_alerta.
    """
    __tablename__ = "alerta_deter"

    id = Column(Integer, primary_key=True, index=True)

    # Identificador vindo do WFS (gid prefixado com workspace para unicidade global)
    id_alerta = Column(String, unique=True, index=True, nullable=False)

    classname = Column(String, index=True)     # Ex.: "DESMATAMENTO_CR", "DEGRADACAO"
    view_date = Column(DateTime, index=True)   # Data de detecção
    area_km2 = Column(Float)                   # Área do alerta em km²
    uc = Column(String)                        # Unidade de conservação (se houver)

    uf = Column(String, default="SP", index=True)   # Sigla do estado
    municipio = Column(String, index=True)
    bioma = Column(String)

    # Geometria MULTIPOLYGON WGS84 (SRID 4326)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326))

    # Controle interno
    ingerido_em = Column(DateTime, server_default=func.now())
