from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.routes.ingestao_routes import router
from app.routes.car_kml_routes import router as car_kml_router
from app.services.car_kml_store import init_car_kml_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_car_kml_store()
    yield


tags_metadata = [
    {
        "name": "Ingestão",
        "description": "Ingestão e consulta de dados de propriedades rurais a partir de fontes públicas (SICAR, INPE, etc.).",
    },
    {
        "name": "Ingestão — CAR KML (MVP)",
        "description": "Consulta a propriedades extraídas do KML CAR em memória (protótipo /app).",
    },
]

app = FastAPI(
    title="Controller de Ingestão de Dados",
    description=(
        "Responsável por carregar e disponibilizar dados de propriedades rurais "
        "oriundos de fontes públicas como SICAR, INPE, ICMBio, FUNAI, INCRA e FCP."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(car_kml_router)
