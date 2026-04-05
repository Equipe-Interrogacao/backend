from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.services.asg_service import ASGService

service = ASGService()


def buscar_analise(cod_car: str, db: Session):
    analise = service.buscar_analise_por_car(db, cod_car)
    if not analise:
        raise HTTPException(status_code=404, detail="Análise ASG não encontrada para este CAR")
    return analise


def listar_analises(db: Session):
    return service.listar_analises(db)


async def criar_analise(dados: dict, db: Session):
    from app.clients.gerenciamento_banco_client import buscar_por_car
    cod_car = dados.get("cod_car")
    if cod_car:
        propriedade = await buscar_por_car(cod_car)
        if not propriedade:
            raise HTTPException(
                status_code=404,
                detail=f"Propriedade '{cod_car}' não encontrada no banco. Ingira os dados primeiro."
            )
    return service.criar_analise(db, dados)
