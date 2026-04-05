from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ImovelCarResponse(BaseModel):
    """Resposta GET /imovel?car= — dados cadastrais para visualização."""

    codigo_car: str = Field(..., description="Código CAR estadual ou federal")
    area_ha: Optional[float] = Field(None, description="Área em hectares")
    municipio: Optional[str] = None
    situacao: Optional[str] = None
    dt_inscricao: Optional[datetime] = None
    dt_analise: Optional[datetime] = None

    class Config:
        from_attributes = True
