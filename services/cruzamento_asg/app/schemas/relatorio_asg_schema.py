from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IndicadorASG(BaseModel):
    categoria: str
    nome: str
    fonte: str
    data_referencia: str
    valor: Optional[float] = None
    unidade: Optional[str] = None
    status: str  # "ok" | "atencao" | "critico" | "pendente"
    detalhe: Optional[str] = None


class RelatorioASGResponse(BaseModel):
    cod_imovel: str
    municipio: Optional[str] = None
    uf: Optional[str] = None
    area_ha: Optional[float] = None
    status_car: Optional[str] = None
    gerado_em: datetime
    indicadores: list[IndicadorASG]
