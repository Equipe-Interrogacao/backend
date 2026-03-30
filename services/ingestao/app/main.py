from fastapi import FastAPI
from app.routes.ingestao_routes import router

tags_metadata = [
    {
        "name": "Ingestão",
        "description": "Ingestão e consulta de dados de propriedades rurais a partir de fontes públicas (SICAR, INPE, etc.).",
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
)

app.include_router(router)
