"""
Schemas Pydantic para as respostas das fontes INPE
(PRODES, DETER e BDQueimadas).
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_validator


# --------------------------------------------------------------------------- #
# Schema de status de ingestão (comum a todas as fontes)
# --------------------------------------------------------------------------- #

class InpeIngestaoStatusResponse(BaseModel):
    rodando: bool
    estado: Optional[str] = None
    total_salvos: int = 0
    total_ignorados: int = 0
    iniciado_em: Optional[str] = None
    concluido_em: Optional[str] = None
    erro: Optional[str] = None


# --------------------------------------------------------------------------- #
# PRODES — desmatamento anual
# --------------------------------------------------------------------------- #

class DesmatamentoProdesResponse(BaseModel):
    id: int
    id_poligono: str
    ano: Optional[int] = None
    area_km2: Optional[float] = None
    classname: Optional[str] = None
    estado: Optional[str] = None
    uf: Optional[str] = "SP"
    municipio: Optional[str] = None
    bioma: Optional[str] = None
    ingerido_em: Optional[datetime] = None
    geometria: Optional[Any] = None

    @field_validator("geometria", mode="before")
    @classmethod
    def serialize_geometria(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping
            return mapping(to_shape(v))
        except Exception:
            return None

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------- #
# DETER — alertas em tempo real
# --------------------------------------------------------------------------- #

class AlertaDeterResponse(BaseModel):
    id: int
    id_alerta: str
    classname: Optional[str] = None
    view_date: Optional[datetime] = None
    area_km2: Optional[float] = None
    uc: Optional[str] = None
    uf: Optional[str] = "SP"
    municipio: Optional[str] = None
    bioma: Optional[str] = None
    ingerido_em: Optional[datetime] = None
    geometria: Optional[Any] = None

    @field_validator("geometria", mode="before")
    @classmethod
    def serialize_geometria(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping
            return mapping(to_shape(v))
        except Exception:
            return None

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------- #
# Queimadas — focos de incêndio
# --------------------------------------------------------------------------- #

class FocoQueimadaResponse(BaseModel):
    id: int
    id_foco: str
    data_hora_gmt: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    satelite: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = "SP"
    pais: Optional[str] = None
    bioma: Optional[str] = None
    frp: Optional[float] = None
    ingerido_em: Optional[datetime] = None
    geometria: Optional[Any] = None

    @field_validator("geometria", mode="before")
    @classmethod
    def serialize_geometria(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        try:
            from geoalchemy2.shape import to_shape
            from shapely.geometry import mapping
            return mapping(to_shape(v))
        except Exception:
            return None

    class Config:
        from_attributes = True
