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
    from app.clients.gerenciamento_banco_client import (
        buscar_por_car,
        buscar_sobreposicao_prodes,
        buscar_deter_por_propriedade,
    )

    cod_car = dados.get("cod_car")
    if not cod_car:
        return service.criar_analise(db, dados)

    propriedade = await buscar_por_car(cod_car)
    if not propriedade:
        raise HTTPException(
            status_code=404,
            detail=f"Propriedade '{cod_car}' não encontrada no banco. Ingira os dados primeiro.",
        )

    # Auto-popula area_desmatada_ha com a área real dentro da propriedade (ST_Intersection)
    if dados.get("area_desmatada_ha") is None:
        sobr = await buscar_sobreposicao_prodes(cod_car)
        dados["area_desmatada_ha"] = sobr.get("area_ha", 0.0)

    # Auto-popula sobreposicao_uc com UCs dos alertas DETER que interceptam a propriedade
    if dados.get("sobreposicao_uc") is None:
        deter = await buscar_deter_por_propriedade(cod_car)
        ucs = sorted({d.get("uc") for d in deter if d.get("uc")})
        if ucs:
            dados["sobreposicao_uc"] = ", ".join(ucs[:5])

    return service.criar_analise(db, dados)
