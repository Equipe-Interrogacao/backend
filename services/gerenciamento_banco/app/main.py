import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database import engine, Base
from app.routes.banco_routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
