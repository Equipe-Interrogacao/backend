from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.config.database import Base


class FocoQueimada(Base):
    """
    Focos de incêndio do BDQueimadas (INPE).

    Fonte: https://queimadas.dgi.inpe.br/api/focos/
    Filtrado por estado=SP e período configurável.
    Geometria armazenada como POINT SRID 4326 (focos são detectados por pixel de satélite).
    Upsert idempotente por id_foco.
    """
    __tablename__ = "foco_queimada"

    id = Column(Integer, primary_key=True, index=True)

    # Identificador único do foco no BDQueimadas
    id_foco = Column(String, unique=True, index=True, nullable=False)

    data_hora_gmt = Column(DateTime, index=True)   # Data/hora de detecção (UTC)
    latitude = Column(Float)
    longitude = Column(Float)
    satelite = Column(String)                      # Satélite detector (ex.: "AQUA_M-T")
    municipio = Column(String, index=True)
    estado = Column(String, default="SP", index=True)  # Sempre SP
    pais = Column(String)
    bioma = Column(String, index=True)
    frp = Column(Float)                            # Fire Radiative Power (MW)

    # Geometria POINT WGS84 (SRID 4326) — focos são pontos
    geometria = Column(Geometry("POINT", srid=4326))

    # Controle interno
    ingerido_em = Column(DateTime, server_default=func.now())
