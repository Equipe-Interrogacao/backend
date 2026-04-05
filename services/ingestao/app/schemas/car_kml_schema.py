from pydantic import BaseModel, Field


class PropriedadeKmlOut(BaseModel):
    """Propriedade extraída do KML CAR (memória), sem persistência no Postgres."""

    cod_car: str = Field(..., description="Código Num_CAR (estadual)")
    municipio: str = Field(..., description="Município")
    latitude: float
    longitude: float
