import logging

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.propriedade import Propriedade
from app.clients.sicar_client import buscar_imovel_por_cod
from app.services.sicar_ingestao_service import _extrair_dados_feature

logger = logging.getLogger(__name__)


class IngestaoService:

    def buscar_por_cod_imovel(self, db: Session, cod_imovel: str):
        return (
            db.query(Propriedade)
            .filter(Propriedade.cod_imovel == cod_imovel)
            .first()
        )

    def listar_propriedades(self, db: Session, limit: int = 100, offset: int = 0):
        return db.query(Propriedade).offset(offset).limit(limit).all()

    def upsert_propriedade(self, db: Session, dados: dict):
        stmt = insert(Propriedade).values(**dados)
        stmt = stmt.on_conflict_do_update(
            index_elements=["cod_imovel"],
            set_={k: stmt.excluded[k] for k in dados if k != "cod_imovel"},
        )
        db.execute(stmt)
        db.commit()
        return self.buscar_por_cod_imovel(db, dados["cod_imovel"])

    async def buscar_ou_ingerir_por_cod(self, db: Session, cod_imovel: str):
        """
        Busca o imóvel no banco local.
        Se não encontrado, consulta o SICAR, salva no banco e retorna.
        Retorna None se não encontrado em nenhuma fonte.
        """
        propriedade = self.buscar_por_cod_imovel(db, cod_imovel)
        if propriedade:
            return propriedade

        logger.info(f"CAR {cod_imovel} não está no banco — buscando no SICAR.")
        feature = await buscar_imovel_por_cod(cod_imovel)
        if not feature:
            return None

        dados = _extrair_dados_feature(feature)
        if not dados:
            logger.warning(f"Feature do SICAR para {cod_imovel} sem geometria válida.")
            return None

        logger.info(f"CAR {cod_imovel} obtido do SICAR — salvando no banco.")
        return self.upsert_propriedade(db, dados)
