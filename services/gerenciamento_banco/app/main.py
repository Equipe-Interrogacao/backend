from fastapi import FastAPI
from app.config.database import engine, Base
from app.routes.banco_routes import router

Base.metadata.create_all(bind=engine)

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
)

app.include_router(router)
