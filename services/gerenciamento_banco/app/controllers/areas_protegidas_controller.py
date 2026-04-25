from sqlalchemy.orm import Session
from app.services.areas_protegidas_service import AreasProtegidasService

service = AreasProtegidasService()


def listar_ucs(db: Session, uf, limit):
    return service.listar_ucs(db, uf, limit)

def listar_tis(db: Session, uf, limit):
    return service.listar_tis(db, uf, limit)

def listar_assentamentos(db: Session, uf, limit):
    return service.listar_assentamentos(db, uf, limit)

def listar_quilombolas(db: Session, uf, limit):
    return service.listar_quilombolas(db, uf, limit)


def ucs_por_propriedade(cod_imovel: str, db: Session):
    return service.ucs_por_propriedade(db, cod_imovel)


def tis_por_propriedade(cod_imovel: str, db: Session):
    return service.tis_por_propriedade(db, cod_imovel)


def assentamentos_por_propriedade(cod_imovel: str, db: Session):
    return service.assentamentos_por_propriedade(db, cod_imovel)


def quilombolas_por_propriedade(cod_imovel: str, db: Session):
    return service.quilombolas_por_propriedade(db, cod_imovel)
