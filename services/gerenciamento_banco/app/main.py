import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config.database import engine, Base, get_db
from app.routes.banco_routes import router
from app.routes.imovel_routes import router as imovel_router
from app.routes.inpe_routes import router as inpe_router
from app.routes.areas_protegidas_routes import router as areas_protegidas_router

# Registra modelos no metadata antes do create_all
from app.models.imovel import Imovel  # noqa: F401
from app.models.inpe_models import DesmatamentoProdes, AlertaDeter, FocoQueimada  # noqa: F401
from app.models.areas_protegidas_models import (  # noqa: F401
    UnidadeConservacao, TerraIndigena, Assentamento, Quilombola,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria tabelas na subida. Em testes, definir SKIP_DB_INIT=1 para não conectar ao Postgres."""
    if os.getenv("SKIP_DB_INIT") != "1":
        for tentativa in range(1, 16):
            try:
                Base.metadata.create_all(bind=engine)
                logger.info("Tabelas criadas/verificadas com sucesso.")
                break
            except Exception as exc:
                logger.warning(f"create_all tentativa {tentativa}/15 falhou: {exc}")
                if tentativa < 15:
                    await asyncio.sleep(3)
                else:
                    logger.error("Não foi possível criar as tabelas após 15 tentativas.")
    yield


tags_metadata = [
    {
        "name": "Gerenciamento do Banco",
        "description": (
            "CRUD de propriedades rurais no banco de dados PostgreSQL + PostGIS. "
            "Ponto central de leitura e escrita geoespacial do sistema."
        ),
    },
    {
        "name": "Imóvel CAR",
        "description": "Consulta de imóvel por código CAR na tabela imovel (SCRUM-3).",
    },
]

app = FastAPI(
    title="Controller de Gerenciamento do Banco",
    description=(
        "Responsável pelo gerenciamento direto do banco de dados relacional "
        "(PostgreSQL + PostGIS), expondo operações de criação, consulta e remoção "
        "de propriedades rurais com suporte a dados geográficos."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(imovel_router)
app.include_router(inpe_router)
app.include_router(areas_protegidas_router)


@app.get("/health", tags=["Health"])
def health(db: Session = Depends(get_db)):
    from app.models.propriedade import Propriedade
    total = db.query(func.count(Propriedade.id)).scalar() or 0
    total_sp = db.query(func.count(Propriedade.id)).filter(Propriedade.uf == "SP").scalar() or 0
    total_prodes = db.query(func.count(DesmatamentoProdes.id)).scalar() or 0
    total_deter = db.query(func.count(AlertaDeter.id)).scalar() or 0
    total_focos = db.query(func.count(FocoQueimada.id)).scalar() or 0
    total_uc = db.query(func.count(UnidadeConservacao.id)).scalar() or 0
    total_ti = db.query(func.count(TerraIndigena.id)).scalar() or 0
    total_assentamento = db.query(func.count(Assentamento.id)).scalar() or 0
    total_quilombola = db.query(func.count(Quilombola.id)).scalar() or 0
    return {
        "sicarSpDisponivel": total_sp > 0,
        "total": total,
        "total_sp": total_sp,
        "total_prodes": total_prodes,
        "total_deter": total_deter,
        "total_focos": total_focos,
        "total_uc": total_uc,
        "total_ti": total_ti,
        "total_assentamento": total_assentamento,
        "total_quilombola": total_quilombola,
    }
