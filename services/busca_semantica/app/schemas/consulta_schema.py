from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConsultaCreate(BaseModel):
    pergunta: str
    cod_imovel: Optional[str] = None

    @property
    def cod_car(self) -> Optional[str]:
        return self.cod_imovel


class ConsultaResponse(BaseModel):
    id: int
    pergunta: str
    resposta: Optional[str] = None
    cod_car: Optional[str] = None
    cod_imovel: Optional[str] = None
    intencao_detectada: Optional[str] = None
    confianca: float = 0.0
    dados: Optional[dict] = None
    criado_em: datetime

    class Config:
        from_attributes = True
