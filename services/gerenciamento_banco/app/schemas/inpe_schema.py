from pydantic import BaseModel, field_validator
from typing import Optional, Any
from datetime import datetime


def _serialize_geom(v):
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
    def _geom(cls, v):
        return _serialize_geom(v)

    class Config:
        from_attributes = True


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
    def _geom(cls, v):
        return _serialize_geom(v)

    class Config:
        from_attributes = True


class FocoQueimadaResponse(BaseModel):
    id: int
    id_foco: str
    data_hora_gmt: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    satelite: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    pais: Optional[str] = None
    bioma: Optional[str] = None
    frp: Optional[float] = None
    ingerido_em: Optional[datetime] = None
    geometria: Optional[Any] = None

    @field_validator("geometria", mode="before")
    @classmethod
    def _geom(cls, v):
        return _serialize_geom(v)

    class Config:
        from_attributes = True
