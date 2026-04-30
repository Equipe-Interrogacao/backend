from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.controllers import asg_controller
from app.schemas.asg_schema import AnaliseASGBase, AnaliseASGResponse
from app.schemas.relatorio_asg_schema import RelatorioIndicadoresResponse
from app.services.relatorio_asg_service import gerar_relatorio

router = APIRouter(prefix="/asg", tags=["Cruzamento ASG"])


@router.get(
    "/analises",
    response_model=list[AnaliseASGResponse],
    summary="Listar análises ASG",
    description="Retorna todas as análises ASG geradas para propriedades rurais.",
)
def listar(db: Session = Depends(get_db)):
    return asg_controller.listar_analises(db)


@router.get(
    "/analises/{cod_car}",
    response_model=AnaliseASGResponse,
    summary="Buscar análise ASG por CAR",
    description=(
        "Retorna os indicadores ASG de uma propriedade: desmatamento, déficit de APP, "
        "déficit de Reserva Legal e sobreposições com áreas protegidas."
    ),
    responses={404: {"description": "Análise ASG não encontrada para este CAR"}},
)
def buscar(cod_car: str, db: Session = Depends(get_db)):
    return asg_controller.buscar_analise(cod_car, db)


@router.get(
    "/relatorio/{cod_imovel:path}",
    response_model=RelatorioIndicadoresResponse,
    summary="Relatório ASG completo por propriedade",
    description=(
        "Compõe indicadores ASG (Ambiental, Social, Governança) para a propriedade "
        "combinando dados INPE (PRODES, DETER, Queimadas) e Áreas Protegidas "
        "(UC, TI, Assentamento, Quilombola). Cada indicador inclui fonte e data de referência."
    ),
    responses={404: {"description": "Propriedade não encontrada"}},
)
async def relatorio_asg(cod_imovel: str):
    relatorio = await gerar_relatorio(cod_imovel)
    if not relatorio:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return relatorio


@router.post(
    "/analises",
    response_model=AnaliseASGResponse,
    status_code=201,
    summary="Criar análise ASG",
    description="Registra uma nova análise ASG para uma propriedade rural.",
)
async def criar(payload: AnaliseASGBase, db: Session = Depends(get_db)):
    return await asg_controller.criar_analise(payload.model_dump(), db)
