from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AnaliseASGBase(BaseModel):
    cod_car: str
    area_desmatada_ha: Optional[float] = 0
    deficit_app_ha: Optional[float] = 0
    deficit_reserva_legal_ha: Optional[float] = 0
    sobreposicao_uc: Optional[str] = None
    sobreposicao_ti: Optional[str] = None


class AnaliseASGResponse(AnaliseASGBase):
    id: int
    criado_em: datetime

    class Config:
        from_attributes = True
