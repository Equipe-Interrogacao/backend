from pydantic import BaseModel
from typing import Optional


class PropriedadeCreate(BaseModel):
    cod_car: str
    nome_proprietario: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = "SP"
    area_total_ha: Optional[float] = None


class PropriedadeResponse(PropriedadeCreate):
    id: int

    class Config:
        from_attributes = True
