"""
Queries espaciais para Áreas Protegidas (UC, TI, Assentamento, Quilombola).
Usa ST_Intersects para encontrar áreas que se sobrepõem à geometria da propriedade.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.areas_protegidas_models import (
    Assentamento,
    Quilombola,
    TerraIndigena,
    UnidadeConservacao,
)
from app.models.propriedade import Propriedade


def _prop_geom_subq(cod_imovel: str):
    return (
        select(Propriedade.geometria)
        .where(Propriedade.cod_imovel == cod_imovel)
        .scalar_subquery()
    )


class AreasProtegidasService:

    def listar_ucs(self, db: Session, uf: str | None = None, limit: int = 500) -> list:
        q = db.query(UnidadeConservacao)
        if uf:
            q = q.filter(UnidadeConservacao.uf.ilike(f"%{uf.upper()}%"))
        return q.limit(limit).all()

    def listar_tis(self, db: Session, uf: str | None = None, limit: int = 500) -> list:
        q = db.query(TerraIndigena)
        if uf:
            q = q.filter(TerraIndigena.uf.ilike(f"%{uf.upper()}%"))
        return q.limit(limit).all()

    def listar_assentamentos(self, db: Session, uf: str | None = None, limit: int = 500) -> list:
        q = db.query(Assentamento)
        if uf:
            q = q.filter(Assentamento.uf == uf.upper())
        return q.limit(limit).all()

    def listar_quilombolas(self, db: Session, uf: str | None = None, limit: int = 500) -> list:
        q = db.query(Quilombola)
        if uf:
            q = q.filter(Quilombola.uf == uf.upper())
        return q.limit(limit).all()

    def ucs_por_propriedade(self, db: Session, cod_imovel: str) -> list:
        geom = _prop_geom_subq(cod_imovel)
        return (
            db.query(UnidadeConservacao)
            .filter(func.ST_Intersects(UnidadeConservacao.geometria, geom))
            .all()
        )

    def tis_por_propriedade(self, db: Session, cod_imovel: str) -> list:
        geom = _prop_geom_subq(cod_imovel)
        return (
            db.query(TerraIndigena)
            .filter(func.ST_Intersects(TerraIndigena.geometria, geom))
            .all()
        )

    def assentamentos_por_propriedade(self, db: Session, cod_imovel: str) -> list:
        geom = _prop_geom_subq(cod_imovel)
        return (
            db.query(Assentamento)
            .filter(func.ST_Intersects(Assentamento.geometria, geom))
            .all()
        )

    def quilombolas_por_propriedade(self, db: Session, cod_imovel: str) -> list:
        geom = _prop_geom_subq(cod_imovel)
        return (
            db.query(Quilombola)
            .filter(func.ST_Intersects(Quilombola.geometria, geom))
            .all()
        )
