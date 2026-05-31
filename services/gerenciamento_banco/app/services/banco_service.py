from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models.propriedade import Propriedade


class BancoService:

    def listar_propriedades(
        self,
        db: Session,
        uf: str | None = None,
        municipio: str | None = None,
        status_imovel: str | None = None,
        limit: int = 100,
        offset: int = 0,
        bbox: tuple | None = None,
    ):
        from sqlalchemy import func
        query = db.query(Propriedade)
        if uf:
            query = query.filter(Propriedade.uf == uf.upper())
        if municipio:
            query = query.filter(Propriedade.municipio.ilike(f"%{municipio}%"))
        if status_imovel:
            query = query.filter(Propriedade.status_imovel == status_imovel.upper())
        if bbox:
            lon_min, lat_min, lon_max, lat_max = bbox
            envelope = func.ST_MakeEnvelope(lon_min, lat_min, lon_max, lat_max, 4326)
            query = query.filter(func.ST_Intersects(Propriedade.geometria, envelope))
        return query.offset(offset).limit(limit).all()

    def buscar_por_id(self, db: Session, id: int):
        return db.query(Propriedade).filter(Propriedade.id == id).first()

    def buscar_por_cod_imovel(self, db: Session, cod_imovel: str):
        return (
            db.query(Propriedade)
            .filter(Propriedade.cod_imovel == cod_imovel)
            .first()
        )

    def upsert_propriedade(self, db: Session, dados: dict):
        stmt = insert(Propriedade).values(**dados)
        stmt = stmt.on_conflict_do_update(
            index_elements=["cod_imovel"],
            set_={k: stmt.excluded[k] for k in dados if k != "cod_imovel"},
        )
        db.execute(stmt)
        db.commit()
        return self.buscar_por_cod_imovel(db, dados["cod_imovel"])

    def deletar_propriedade(self, db: Session, id: int):
        propriedade = self.buscar_por_id(db, id)
        if propriedade:
            db.delete(propriedade)
            db.commit()
        return propriedade

    def contar_por_uf(self, db: Session):
        from sqlalchemy import func
        return (
            db.query(Propriedade.uf, func.count(Propriedade.id).label("total"))
            .group_by(Propriedade.uf)
            .all()
        )

    def buscar_proximas_por_coordenadas(
        self,
        db: Session,
        lat: float,
        lon: float,
        raio_m: int = 5000,
        limit: int = 10,
    ):
        """Propriedades cujo polígono está dentro de raio_m metros do ponto (lat, lon)."""
        from sqlalchemy import func, cast
        from geoalchemy2.types import Geography

        ponto = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        return (
            db.query(Propriedade)
            .filter(
                func.ST_DWithin(
                    cast(Propriedade.geometria, Geography),
                    cast(ponto, Geography),
                    raio_m,
                )
            )
            .limit(limit)
            .all()
        )
