import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database import engine, Base
from app.routes.ingestao_routes import router
from app.routes.car_kml_routes import router as car_kml_router
from app.services.car_kml_store import init_car_kml_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_car_kml_store()
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
