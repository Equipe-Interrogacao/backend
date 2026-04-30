from pydantic import BaseModel
from typing import Optional
from datetime import date
from enum import Enum


class FonteINPE(str, Enum):
    deter = "deter"
    prodes = "prodes"
    queimadas = "queimadas"


class PassivoAmbiental(BaseModel):
    fonte: FonteINPE
    tipo_alerta: str
    data_referencia: date
    area_ha: float
    geometria_intersecao: Optional[dict] = None


class PassivoAmbientalResponse(BaseModel):
    cod_imovel: str
    total_alertas: int
    area_total_passivos_ha: float
    passivos: list[PassivoAmbiental]
