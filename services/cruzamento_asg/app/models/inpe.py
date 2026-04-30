from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Index
from geoalchemy2 import Geometry
from app.config.database import Base


class AlertaDeter(Base):
    __tablename__ = "alerta_deter"

    id = Column(Integer, primary_key=True, index=True)
    cod_alerta = Column(String, index=True)
    classe = Column(String, index=True)
    data_deteccao = Column(Date, index=True)
    area_km2 = Column(Float)
    uf = Column(String(2), index=True)
    municipio = Column(String)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    __table_args__ = (
        Index("idx_alerta_deter_geom", "geometria", postgresql_using="gist"),
    )


class DesmatamentoProdes(Base):
    __tablename__ = "desmatamento_prodes"

    id = Column(Integer, primary_key=True, index=True)
    ano_referencia = Column(Integer, index=True)
    classe = Column(String, index=True)
    area_km2 = Column(Float)
    uf = Column(String(2), index=True)
    municipio = Column(String)
    geometria = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    __table_args__ = (
        Index("idx_desmatamento_prodes_geom", "geometria", postgresql_using="gist"),
    )


class FocoQueimada(Base):
    __tablename__ = "foco_queimada"

    id = Column(Integer, primary_key=True, index=True)
    data_hora = Column(DateTime, index=True)
    satelite = Column(String)
    bioma = Column(String)
    uf = Column(String(2), index=True)
    municipio = Column(String)
    potencia_frp = Column(Float)
    geometria = Column(Geometry("POINT", srid=4326), nullable=False)

    __table_args__ = (
        Index("idx_foco_queimada_geom", "geometria", postgresql_using="gist"),
    )
