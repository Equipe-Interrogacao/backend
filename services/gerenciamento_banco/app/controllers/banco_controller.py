from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.services.banco_service import BancoService

service = BancoService()


def listar_propriedades(
    db: Session,
    uf: str | None,
    municipio: str | None,
    status_imovel: str | None,
    limit: int,
    offset: int,
    bbox: str | None = None,
):
    parsed_bbox = None
    if bbox:
        try:
            parts = [float(x) for x in bbox.split(",")]
            if len(parts) == 4:
                parsed_bbox = tuple(parts)
        except ValueError:
            pass
    return service.listar_propriedades(
        db,
        uf=uf,
        municipio=municipio,
        status_imovel=status_imovel,
        limit=limit,
        offset=offset,
        bbox=parsed_bbox,
    )


def buscar_propriedade(id: int, db: Session):
    propriedade = service.buscar_por_id(db, id)
    if not propriedade:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return propriedade


def buscar_por_cod_imovel(cod_imovel: str, db: Session):
    propriedade = service.buscar_por_cod_imovel(db, cod_imovel)
    if not propriedade:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return propriedade


def upsert_propriedade(dados: dict, db: Session):
    return service.upsert_propriedade(db, dados)


def deletar_propriedade(id: int, db: Session):
    propriedade = service.deletar_propriedade(db, id)
    if not propriedade:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return {"mensagem": f"Propriedade {id} deletada com sucesso"}


def stats_por_uf(db: Session):
    rows = service.contar_por_uf(db)
    return [{"uf": r[0], "total": r[1]} for r in rows]


def buscar_proximas(lat: float, lon: float, raio_m: int, limit: int, db: Session):
    return service.buscar_proximas_por_coordenadas(db, lat, lon, raio_m, limit)
