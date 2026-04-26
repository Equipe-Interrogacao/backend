from fastapi import FastAPI
from app.routes.asg_routes import router
from app.config.database import Base, engine
from app.models.analise_asg import AnaliseASG

tags_metadata = [
    {
        "name": "Cruzamento ASG",
        "description": (
            "Cruzamento de dados ambientais, sociais e fundiários para geração de "
            "indicadores ASG (Ambiental, Social e Governança) de propriedades rurais."
        ),
    },
]

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
)

app.include_router(router)

# Ensure DB tables exist when the app starts (useful for local/dev Docker)
Base.metadata.create_all(bind=engine)
