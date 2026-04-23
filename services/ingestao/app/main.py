import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database import engine, Base
from app.routes.ingestao_routes import router
from app.routes.car_kml_routes import router as car_kml_router
from app.routes.inpe_routes import router as inpe_router
from app.routes.areas_protegidas_routes import router as areas_protegidas_router
from app.services.car_kml_store import init_car_kml_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria tabelas na subida. Em testes, definir SKIP_DB_INIT=1 para não conectar ao Postgres."""
    init_car_kml_store()
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
        "name": "Ingestão",
        "description": (
            "Ingestão e consulta de dados de propriedades rurais a partir do SICAR "
            "(Sistema de Cadastro Ambiental Rural — geoserver.car.gov.br). "
            "Use POST /ingestao/sicar/ingerir para baixar todos os imóveis de um estado."
        ),
    },
    {
        "name": "Ingestão — CAR KML (MVP)",
        "description": "Consulta a propriedades extraídas do KML CAR em memória (protótipo /app).",
    },
    {
        "name": "Ingestão — INPE",
        "description": (
            "Ingestão de dados ambientais do INPE filtrados para SP: "
            "desmatamento anual (PRODES/TerraBrasilis), alertas em tempo-real "
            "(DETER/TerraBrasilis) e focos de incêndio (BDQueimadas). "
            "Use POST /ingestao/inpe/{prodes|deter|queimadas}/ingerir para iniciar "
            "e GET /ingestao/inpe/{fonte}/status para acompanhar."
        ),
    },
    {
        "name": "Ingestão — Áreas Protegidas",
        "description": (
            "Ingestão de camadas de áreas protegidas: "
            "Unidades de Conservação (ICMBio/CNUC), Terras Indígenas (FUNAI), "
            "Assentamentos (INCRA) e Territórios Quilombolas (FCP/INCRA). "
            "Use POST /ingestao/areas-protegidas/{uc|ti|assentamento|quilombola}/ingerir."
        ),
    },
]

app = FastAPI(
    title="Controller de Ingestão de Dados",
    description=(
        "Responsável por carregar dados de propriedades rurais do SICAR via WFS público "
        "e persistir no PostgreSQL + PostGIS. Suporta ingestão completa por estado "
        "com paginação automática e upsert idempotente."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(car_kml_router)
app.include_router(inpe_router)
app.include_router(areas_protegidas_router)
