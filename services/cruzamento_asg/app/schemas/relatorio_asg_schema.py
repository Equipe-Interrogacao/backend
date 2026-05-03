"""
Schemas Pydantic para os dois endpoints de relatório ASG:
  - RelatorioASGResponse         → Task 9: consolidado com seções + índice de risco
  - RelatorioIndicadoresResponse → Task 10: cards simples para o frontend
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

# ── Fontes canônicas ──────────────────────────────────────────────────────────

FONTE_SICAR = "SICAR — cadastro de imóveis rurais (GeoServer / ingestão)"
FONTE_INPE_PRODES = "INPE — PRODES (desmatamento histórico)"
FONTE_INPE_DETER = "INPE — DETER (alertas de desmatamento)"
FONTE_INPE_FOCOS = "INPE / BDQueimadas — focos de queimada"
FONTE_AP = "Áreas protegidas — ICMBio/MMA (sobreposição; integração Task 8)"

# Task 9 — Relatório ASG consolidado (JSON + GPKG + GeoJSON)

class IndicadorComFonte(BaseModel):
    fonte: str
    data_referencia: Optional[str] = Field(default=None)

class DadosPropriedadeSICAR(BaseModel):
    cod_imovel: Optional[str] = None
    uf: Optional[str] = None
    municipio: Optional[str] = None
    status_imovel: Optional[str] = None
    area_ha: Optional[float] = None
    condicao: Optional[str] = None
    dat_criacao: Optional[Union[datetime, str]] = None
    ingerido_em: Optional[Union[datetime, str]] = None
    possui_geometria: bool = False

class SecaoPropriedade(IndicadorComFonte):
    dados: Optional[DadosPropriedadeSICAR] = None

class ProdesSobreposicao(IndicadorComFonte):
    n_poligonos: int = 0
    area_sobreposta_ha: float = 0.0
    por_ano: list[dict[str, Any]] = Field(default_factory=list)

class DeterResumo(IndicadorComFonte):
    n_alertas: int = 0
    ucs_mencionadas: list[str] = Field(default_factory=list)

class SecaoDesmatamento(BaseModel):
    prodes: ProdesSobreposicao
    deter: DeterResumo
    alertas_deter: list[dict[str, Any]] = Field(default_factory=list)
    poligonos_prodes: list[dict[str, Any]] = Field(default_factory=list)

class FocosResumo(IndicadorComFonte):
    n_focos: int = 0

class SecaoQueimadas(BaseModel):
    resumo: FocosResumo
    focos: list[dict[str, Any]] = Field(default_factory=list)

class AreasProtegidasResumo(IndicadorComFonte):
    n_sobreposicoes: int = 0
    nota: Optional[str] = None

class SecaoAreasProtegidas(BaseModel):
    resumo: AreasProtegidasResumo
    feicoes: list[dict[str, Any]] = Field(default_factory=list)

class ResumoASG(BaseModel):
    indice_risco: float = Field(..., ge=0, le=100)
    nivel: str
    desmatamento_relativo: Optional[float] = None
    peso_ap: float = 0.0

class RelatorioASGResponse(BaseModel):
    """Relatório ASG consolidado — Task 9. Endpoint: /relatorio/car/{cod_imovel}/asg"""
    cod_imovel: str
    gerado_em: datetime
    propriedade: SecaoPropriedade
    desmatamento: SecaoDesmatamento
    queimadas: SecaoQueimadas
    areas_protegidas: SecaoAreasProtegidas
    resumo_asg: ResumoASG

# Task 10 — Indicadores ASG (cards do frontend)

class IndicadorASG(BaseModel):
    categoria: str
    nome: str
    fonte: str
    data_referencia: str
    valor: Optional[float] = None
    unidade: Optional[str] = None
    status: str
    detalhe: Optional[str] = None

class RelatorioIndicadoresResponse(BaseModel):
    """Relatório ASG simplificado — Task 10. Endpoint: /asg/relatorio/{cod_imovel}"""
    cod_imovel: str
    municipio: Optional[str] = None
    uf: Optional[str] = None
    area_ha: Optional[float] = None
    status_car: Optional[str] = None
    gerado_em: datetime
    indicadores: list[IndicadorASG]
