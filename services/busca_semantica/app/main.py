from fastapi import FastAPI
from app.routes.busca_routes import router

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

app.include_router(router)
