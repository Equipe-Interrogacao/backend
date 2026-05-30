"""
InpeService — queries textuais e espaciais (PostGIS) para PRODES, DETER e Focos.

Métodos *_por_propriedade usam ST_Intersects / ST_DWithin diretamente na geometria
da propriedade SICAR, evitando filtros imprecisos por município.

sobreposicao_prodes_por_propriedade devolve a área real de desmatamento dentro do
polígono da propriedade via ST_Intersection, pronta para análises ASG.
"""

from sqlalchemy import func, extract, select
from sqlalchemy.orm import Session
from geoalchemy2.types import Geography

from app.models.inpe_models import AlertaDeter, DesmatamentoProdes, FocoQueimada
from app.models.propriedade import Propriedade


def _prop_geom_subq(cod_imovel: str):
    """Subquery que retorna a geometria da propriedade pelo código CAR."""
    return (
        select(Propriedade.geometria)
        .where(Propriedade.cod_imovel == cod_imovel)
        .scalar_subquery()
    )


class InpeService:


    def listar_prodes_por_propriedade(self, db: Session, cod_imovel: str) -> list:
        """Polígonos PRODES que interceptam exatamente a geometria da propriedade."""
        geom = _prop_geom_subq(cod_imovel)
        return (
            db.query(DesmatamentoProdes)
            .filter(func.ST_Intersects(DesmatamentoProdes.geometria, geom))
            .all()
        )

    def sobreposicao_prodes_por_propriedade(self, db: Session, cod_imovel: str) -> dict:
        """
        Calcula a área real de desmatamento (ha) DENTRO da propriedade via
        ST_Intersection + ST_Area(geography).
        Retorna: {n_poligonos, area_ha, por_ano: [{ano, area_ha}]}
        """
        geom = _prop_geom_subq(cod_imovel)

        # Área total sobreposta
        row = db.execute(
            select(
                func.count(DesmatamentoProdes.id).label("n"),
                func.sum(
                    func.ST_Area(
                        func.cast(
                            func.ST_Intersection(DesmatamentoProdes.geometria, geom),
                            Geography(srid=4326),
                        )
                    )
                ).label("area_m2"),
            ).where(func.ST_Intersects(DesmatamentoProdes.geometria, geom))
        ).first()

        n = row.n or 0
        area_ha = round((row.area_m2 or 0) / 10_000, 4)

        # Detalhamento por ano
        por_ano_rows = db.execute(
            select(
                DesmatamentoProdes.ano,
                func.sum(
                    func.ST_Area(
                        func.cast(
                            func.ST_Intersection(DesmatamentoProdes.geometria, geom),
                            Geography(srid=4326),
                        )
                    )
                ).label("area_m2"),
            )
            .where(func.ST_Intersects(DesmatamentoProdes.geometria, geom))
            .group_by(DesmatamentoProdes.ano)
            .order_by(DesmatamentoProdes.ano)
        ).all()

        por_ano = [
            {"ano": r.ano, "area_ha": round((r.area_m2 or 0) / 10_000, 4)}
            for r in por_ano_rows
        ]

        return {"n_poligonos": n, "area_ha": area_ha, "por_ano": por_ano}



    def listar_deter_por_propriedade(self, db: Session, cod_imovel: str) -> list:
        """Alertas DETER que interceptam a geometria da propriedade."""
        geom = _prop_geom_subq(cod_imovel)
        return (
            db.query(AlertaDeter)
            .filter(func.ST_Intersects(AlertaDeter.geometria, geom))
            .all()
        )

    # ──────────────────────────────────────────────── FOCOS — por propriedade

    def listar_focos_por_propriedade(self, db: Session, cod_imovel: str) -> list:
        """Focos de queimada DENTRO da geometria da propriedade via ST_Within."""
        geom = _prop_geom_subq(cod_imovel)
        return (
            db.query(FocoQueimada)
            .filter(func.ST_Within(FocoQueimada.geometria, geom))
            .all()
        )

    def listar_prodes(
        self,
        db: Session,
        uf: str | None = None,
        ano: int | None = None,
        municipio: str | None = None,
        bioma: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        q = db.query(DesmatamentoProdes)
        if uf:
            q = q.filter(DesmatamentoProdes.uf == uf.upper())
        if ano:
            q = q.filter(DesmatamentoProdes.ano == ano)
        if municipio:
            q = q.filter(DesmatamentoProdes.municipio.ilike(f"%{municipio}%"))
        if bioma:
            q = q.filter(DesmatamentoProdes.bioma.ilike(f"%{bioma}%"))
        return q.offset(offset).limit(limit).all()

    def buscar_prodes_por_id(self, db: Session, id_poligono: str):
        return db.query(DesmatamentoProdes).filter(
            DesmatamentoProdes.id_poligono == id_poligono
        ).first()

    def stats_prodes(self, db: Session, uf: str = "SP"):
        rows = (
            db.query(
                DesmatamentoProdes.ano,
                func.count(DesmatamentoProdes.id).label("total"),
                func.sum(DesmatamentoProdes.area_km2).label("area_total_km2"),
            )
            .filter(DesmatamentoProdes.uf == uf.upper())
            .group_by(DesmatamentoProdes.ano)
            .order_by(DesmatamentoProdes.ano)
            .all()
        )
        return [{"ano": r[0], "total": r[1], "area_total_km2": round(r[2] or 0, 4)} for r in rows]

    # ─────────────────────────────────────────── DETER — filtros textuais

    def listar_deter(
        self,
        db: Session,
        uf: str | None = None,
        ano: int | None = None,
        municipio: str | None = None,
        classname: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        q = db.query(AlertaDeter)
        if uf:
            q = q.filter(AlertaDeter.uf == uf.upper())
        if ano:
            q = q.filter(func.extract("year", AlertaDeter.view_date) == ano)
        if municipio:
            q = q.filter(AlertaDeter.municipio.ilike(f"%{municipio}%"))
        if classname:
            q = q.filter(AlertaDeter.classname.ilike(f"%{classname}%"))
        return q.offset(offset).limit(limit).all()

    def buscar_deter_por_id(self, db: Session, id_alerta: str):
        return db.query(AlertaDeter).filter(AlertaDeter.id_alerta == id_alerta).first()

    # ─────────────────────────────────────────── FOCOS — filtros textuais

    def listar_focos(
        self,
        db: Session,
        estado: str | None = None,
        municipio: str | None = None,
        bioma: str | None = None,
        ano: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        q = db.query(FocoQueimada)
        if estado:
            q = q.filter(FocoQueimada.estado == estado.upper())
        if municipio:
            q = q.filter(FocoQueimada.municipio.ilike(f"%{municipio}%"))
        if bioma:
            q = q.filter(FocoQueimada.bioma.ilike(f"%{bioma}%"))
        if ano:
            q = q.filter(extract("year", FocoQueimada.data_hora_gmt) == ano)
        return q.offset(offset).limit(limit).all()

    def buscar_foco_por_id(self, db: Session, id_foco: str):
        return db.query(FocoQueimada).filter(FocoQueimada.id_foco == id_foco).first()

    def stats_focos(self, db: Session, estado: str = "SP"):
        rows = (
            db.query(
                extract("year", FocoQueimada.data_hora_gmt).label("ano"),
                func.count(FocoQueimada.id).label("total"),
            )
            .filter(FocoQueimada.estado == estado.upper())
            .group_by("ano")
            .order_by("ano")
            .all()
        )
        return [{"ano": int(r[0]) if r[0] else None, "total": r[1]} for r in rows]
