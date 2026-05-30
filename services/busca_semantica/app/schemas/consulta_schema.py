from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from typing import Optional, Any
from datetime import datetime


class ConsultaCreate(BaseModel):
    pergunta: str
    cod_imovel: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("cod_imovel", "cod_car"),
        serialization_alias="cod_imovel",
    )
    municipio_contexto: Optional[str] = None
    intencao_contexto: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

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
    dados: Optional[Any] = None
    acao: Optional[str] = None
    municipio_detectado: Optional[str] = None
    coordenadas_detectadas: Optional[list[float]] = None
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
