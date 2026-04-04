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
    ):
        query = db.query(Propriedade)
        if uf:
            query = query.filter(Propriedade.uf == uf.upper())
        if municipio:
            query = query.filter(Propriedade.municipio.ilike(f"%{municipio}%"))
        if status_imovel:
            query = query.filter(Propriedade.status_imovel == status_imovel.upper())
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
    
    def obter_geometria_geojson(self, db: Session, cod_imovel: str):
        """
        Busca geometria no PostGIS, converte para EPSG:4674 e retorna GeoJSON + BBOX.
        O uso de filtros sobre 'cod_imovel' aproveita o índice unique.
        """
        sql = text("""
            SELECT 
                cod_imovel,
                area,
                ST_AsGeoJSON(ST_Transform(geometria, 4674)) as geojson,
                ST_Extent(ST_Transform(geometria, 4674)) OVER() as bbox
            FROM propriedades
            WHERE cod_imovel = :cod
        """)
        
        result = db.execute(sql, {"cod": cod_imovel}).first()
        
        if not result:
            return None
            
        return {
            "codigo_car": result.cod_imovel,
            "area_ha": result.area,
            "geojson": json.loads(result.geojson),
            "bbox": str(result.bbox) if result.bbox else None
        }
        
