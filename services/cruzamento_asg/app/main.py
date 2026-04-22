from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database import Base, engine
from app.routes.asg_routes import router as asg_router
from app.routes.passivo_routes import router as passivo_router

import app.models.inpe  # noqa: F401 — registra modelos INPE no metadata

tags_metadata = [
    {
        "name": "Cruzamento ASG",
        "description": (
            "Cruzamento de dados ambientais, sociais e fundiários para geração de "
            "indicadores ASG (Ambiental, Social e Governança) de propriedades rurais."
        ),
    },
    {
        "name": "Passivos Ambientais",
        "description": (
            "Cruzamento do polígono CAR com alertas INPE (DETER, PRODES, queimadas) "
            "para identificação de passivos ambientais com fonte, data e área."
        ),
    },
]


@asynccontextmanager
async def lifespan(application: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Controller de Cruzamento ASG",
    description=(
        "Responsável por cruzar dados geoespaciais públicos e gerar indicadores ASG, "
        "identificando desmatamento, déficit de APP/Reserva Legal e sobreposições "
        "com áreas protegidas, terras indígenas e assentamentos."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(asg_router)
app.include_router(passivo_router)
