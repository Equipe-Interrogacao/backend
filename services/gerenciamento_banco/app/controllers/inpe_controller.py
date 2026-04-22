from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.services.inpe_service import InpeService

service = InpeService()


# ------------------------------------------------------------------ PRODES

def listar_prodes(db, uf, ano, municipio, bioma, limit, offset):
    return service.listar_prodes(db, uf, ano, municipio, bioma, limit, offset)


def listar_prodes_por_propriedade(cod_imovel: str, db: Session):
    return service.listar_prodes_por_propriedade(db, cod_imovel)


def sobreposicao_prodes_por_propriedade(cod_imovel: str, db: Session):
    return service.sobreposicao_prodes_por_propriedade(db, cod_imovel)


def buscar_prodes(id_poligono: str, db: Session):
    obj = service.buscar_prodes_por_id(db, id_poligono)
    if not obj:
        raise HTTPException(status_code=404, detail="Polígono PRODES não encontrado")
    return obj


def stats_prodes(db: Session, uf: str = "SP"):
    return service.stats_prodes(db, uf)


# ------------------------------------------------------------------- DETER

def listar_deter(db, uf, municipio, classname, limit, offset):
    return service.listar_deter(db, uf, municipio, classname, limit, offset)


def listar_deter_por_propriedade(cod_imovel: str, db: Session):
    return service.listar_deter_por_propriedade(db, cod_imovel)


def buscar_deter(id_alerta: str, db: Session):
    obj = service.buscar_deter_por_id(db, id_alerta)
    if not obj:
        raise HTTPException(status_code=404, detail="Alerta DETER não encontrado")
    return obj


# ------------------------------------------------------------------ FOCOS

def listar_focos(db, estado, municipio, bioma, ano, limit, offset):
    return service.listar_focos(db, estado, municipio, bioma, ano, limit, offset)


def listar_focos_por_propriedade(cod_imovel: str, db: Session):
    return service.listar_focos_por_propriedade(db, cod_imovel)


def buscar_foco(id_foco: str, db: Session):
    obj = service.buscar_foco_por_id(db, id_foco)
    if not obj:
        raise HTTPException(status_code=404, detail="Foco de queimada não encontrado")
    return obj


def stats_focos(db: Session, estado: str = "SP"):
    return service.stats_focos(db, estado)
