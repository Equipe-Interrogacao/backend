from pydantic import BaseModel
from typing import Optional


class PropriedadeBase(BaseModel):
    cod_car: str
    nome_proprietario: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = "SP"
    area_total_ha: Optional[float] = None


class PropriedadeResponse(PropriedadeBase):
    id: int

    class Config:
        from_attributes = True
