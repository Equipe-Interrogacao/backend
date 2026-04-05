from pydantic import BaseModel, field_validator
from typing import Optional, Any
from datetime import datetime


class PropriedadeBase(BaseModel):
    cod_imovel: str
    status_imovel: Optional[str] = None
    dat_criacao: Optional[datetime] = None
    area: Optional[float] = None
    condicao: Optional[str] = None
    uf: Optional[str] = "SP"
    municipio: Optional[str] = None
    cod_municipio_ibge: Optional[str] = None
    m_fiscal: Optional[str] = None
    tipo_imovel: Optional[str] = None


class PropriedadeResponse(PropriedadeBase):
    id: int
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


class IngestaoStatusResponse(BaseModel):
    rodando: bool
    estado: Optional[str] = None
    total_salvos: int = 0
    total_ignorados: int = 0
    iniciado_em: Optional[str] = None
    concluido_em: Optional[str] = None
    erro: Optional[str] = None
