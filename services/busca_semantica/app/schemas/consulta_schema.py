from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConsultaCreate(BaseModel):
    pergunta: str
    cod_car: Optional[str] = None


class ConsultaResponse(BaseModel):
    id: int
    pergunta: str
    resposta: Optional[str] = None
    cod_car: Optional[str] = None
    criado_em: datetime

    class Config:
        from_attributes = True
