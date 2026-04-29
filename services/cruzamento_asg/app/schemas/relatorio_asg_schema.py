"""
Resposta consolidada do relatório ASG (JSON).
Cada bloco principal inclui fonte e data_referencia conforme user story.
"""

from typing import Any, Optional, Union

from datetime import datetime

from pydantic import BaseModel, Field

# --- Fontes canónicas (exibidas na API) ---
FONTE_SICAR = "SICAR — cadastro de imóveis rurais (GeoServer / ingestão)"
FONTE_INPE_PRODES = "INPE — PRODES (desmatamento histórico)"
FONTE_INPE_DETER = "INPE — DETER (alertas de desmatamento)"
FONTE_INPE_FOCOS = "INPE / BDQueimadas — focos de queimada"
FONTE_AP = "Áreas protegidas — ICMBio/MMA (sobreposição; integração Task 8)"


class IndicadorComFonte(BaseModel):
    """Indicador agregado com rastreabilidade da origem."""

    fonte: str
    data_referencia: Optional[str] = Field(
        default=None,
        description="Data ou período de referência em ISO-8601 ou ano (string).",
    )


class DadosPropriedadeSICAR(BaseModel):
    """Atributos da propriedade SICAR quando existente no banco."""

    cod_imovel: Optional[str] = None
    uf: Optional[str] = None
    municipio: Optional[str] = None
    status_imovel: Optional[str] = None
    area_ha: Optional[float] = Field(default=None, description="Área declarada no SICAR (ha)")
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
    # Mantém lista leve no JSON; export GeoPackage usa geometrias completas do client
    alertas_deter: list[dict[str, Any]] = Field(default_factory=list)
    poligonos_prodes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Resumo dos polígonos (ids); geometria só na export.",
    )


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
    feicoes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Geometrias e atributos quando o endpoint existir (Task 8).",
    )


class ResumoASG(BaseModel):
    """
    Índice de risco 0–100: combina desmatamento relativo, alertas e focos.
    Ver comentário em relatorio_asg_service.calcular_indice_risco.
    """

    indice_risco: float = Field(..., ge=0, le=100)
    nivel: str = Field(..., description='Um de: "baixo", "medio", "alto"')
    desmatamento_relativo: Optional[float] = None
    peso_ap: float = 0.0


class RelatorioASGResponse(BaseModel):
    cod_imovel: str
    gerado_em: datetime = Field(
        description="Timestamp UTC ISO 8601 do momento de geração do relatório."
    )
    propriedade: SecaoPropriedade
    desmatamento: SecaoDesmatamento
    queimadas: SecaoQueimadas
    areas_protegidas: SecaoAreasProtegidas
    resumo_asg: ResumoASG

    model_config = {
        "json_schema_extra": {
            "example": {
                "cod_imovel": "SP-1234-0000-0000-0000-0000-0000-0000-0000-00",
                "gerado_em": "2026-04-22T12:00:00Z",
            }
        }
    }
