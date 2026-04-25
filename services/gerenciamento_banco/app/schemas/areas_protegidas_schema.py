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


class UnidadeConservacaoResponse(BaseModel):
    id: int
    cod_uc: str
    nome: Optional[str] = None
    categoria: Optional[str] = None
    grupo: Optional[str] = None
    esfera: Optional[str] = None
    uf: Optional[str] = None
    area_ha: Optional[float] = None
    ingerido_em: Optional[datetime] = None
    geometria: Optional[Any] = None

    @field_validator("geometria", mode="before")
    @classmethod
    def _geom(cls, v):
        return _serialize_geom(v)

    class Config:
        from_attributes = True


class TerraIndigenaResponse(BaseModel):
    id: int
    cod_ti: str
    nome: Optional[str] = None
    etnia: Optional[str] = None
    fase: Optional[str] = None
    uf: Optional[str] = None
    area_ha: Optional[float] = None
    ingerido_em: Optional[datetime] = None
    geometria: Optional[Any] = None

    @field_validator("geometria", mode="before")
    @classmethod
    def _geom(cls, v):
        return _serialize_geom(v)

    class Config:
        from_attributes = True


class AssentamentoResponse(BaseModel):
    id: int
    cod_sipra: str
    nome: Optional[str] = None
    tipo: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    area_ha: Optional[float] = None
    familias: Optional[int] = None
    dt_criacao: Optional[datetime] = None
    ingerido_em: Optional[datetime] = None
    geometria: Optional[Any] = None

    @field_validator("geometria", mode="before")
    @classmethod
    def _geom(cls, v):
        return _serialize_geom(v)

    class Config:
        from_attributes = True


class QuilombolaResponse(BaseModel):
    id: int
    cod_quilombola: str
    nome: Optional[str] = None
    etnia: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    area_ha: Optional[float] = None
    fase: Optional[str] = None
    dt_publicacao: Optional[datetime] = None
    ingerido_em: Optional[datetime] = None
    geometria: Optional[Any] = None

    @field_validator("geometria", mode="before")
    @classmethod
    def _geom(cls, v):
        return _serialize_geom(v)

    class Config:
        from_attributes = True
