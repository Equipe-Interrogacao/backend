import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.busca_routes import router
from app.config.database import Base, engine
from app.models.consulta import Consulta

tags_metadata = [
    {
        "name": "Busca Semântica",
        "description": (
            "Consultas em linguagem natural sobre propriedades rurais e seus indicadores ASG. "
            "Retorna respostas estruturadas com fontes rastreáveis."
        ),
    },
]

app = FastAPI(
    title="Controller de Busca Semântica",
    description=(
        "Responsável por receber perguntas em linguagem natural — como "
        "'Houve desmatamento recente?' ou 'Existe passivo ambiental?' — "
        "e retornar respostas rápidas e auditáveis com base nos dados ASG."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure required tables exist when the service starts.
Base.metadata.create_all(bind=engine)

app.include_router(router)
