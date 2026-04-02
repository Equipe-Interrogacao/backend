"""
Serviço de ingestão SICAR.

Orquestra a busca paginada de imóveis via WFS (geoserver.car.gov.br) e persiste
no PostgreSQL + PostGIS usando upsert idempotente por cod_imovel.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, shape
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from app.clients.sicar_client import buscar_imoveis_por_estado
from app.models.propriedade import Propriedade

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Status global em memória
# --------------------------------------------------------------------------- #
_status: dict = {
    "rodando": False,
    "estado": None,
    "total_salvos": 0,
    "total_ignorados": 0,
    "iniciado_em": None,
    "concluido_em": None,
    "erro": None,
}


def get_status() -> dict:
    return dict(_status)


# --------------------------------------------------------------------------- #
# Helpers de conversão
# --------------------------------------------------------------------------- #

def _converter_geometria(geojson_geom: dict) -> Optional[object]:
    try:
        geom = shape(geojson_geom)
        if geom.is_empty:
            return None
        if geom.geom_type == "Polygon":
            geom = MultiPolygon([geom])
        elif geom.geom_type != "MultiPolygon":
            geom = MultiPolygon([geom.convex_hull])
        return from_shape(geom, srid=4326)
    except Exception as exc:
        logger.debug(f"Falha ao converter geometria: {exc}")
        return None


def _parse_datetime(val) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


def _extrair_dados_feature(feature: dict) -> Optional[dict]:
    """
    Mapeia os campos reais do GeoServer CAR para o modelo Propriedade.

    Campos da API: cod_imovel, status_imovel, dat_criacao, area, condicao,
                   uf, municipio, cod_municipio_ibge, m_fiscal, tipo_imovel
    """
    props = feature.get("properties") or {}
    geom_json = feature.get("geometry")

    cod_imovel = props.get("cod_imovel")
    if not cod_imovel or not geom_json:
        return None

    geometria = _converter_geometria(geom_json)
    if geometria is None:
        return None

    return {
        "cod_imovel": cod_imovel,
        "status_imovel": props.get("status_imovel"),
        "dat_criacao": _parse_datetime(props.get("dat_criacao")),
        "area": props.get("area"),
        "condicao": props.get("condicao"),
        "uf": props.get("uf", "SP"),
        "municipio": props.get("municipio"),
        "cod_municipio_ibge": str(props.get("cod_municipio_ibge") or ""),
        "m_fiscal": props.get("m_fiscal"),
        "tipo_imovel": props.get("tipo_imovel"),
        "geometria": geometria,
    }


def _upsert_batch(session, registros: list[dict]) -> None:
    stmt = insert(Propriedade).values(registros)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cod_imovel"],
        set_={k: stmt.excluded[k] for k in registros[0] if k != "cod_imovel"},
    )
    session.execute(stmt)
    session.commit()


# --------------------------------------------------------------------------- #
# Função principal — executada como BackgroundTask
# --------------------------------------------------------------------------- #

async def ingerir_estado(estado: str = "SP") -> None:
    global _status

    if _status["rodando"]:
        logger.warning("Ingestão já está em execução. Ignorando nova chamada.")
        return

    _status = {
        "rodando": True,
        "estado": estado,
        "total_salvos": 0,
        "total_ignorados": 0,
        "iniciado_em": datetime.now(timezone.utc).isoformat(),
        "concluido_em": None,
        "erro": None,
    }

    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/asg_db"
    )
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        async for pagina in buscar_imoveis_por_estado(estado):
            registros = []
            for feature in pagina:
                dados = _extrair_dados_feature(feature)
                if dados:
                    registros.append(dados)
                else:
                    _status["total_ignorados"] += 1

            if registros:
                _upsert_batch(db, registros)
                _status["total_salvos"] += len(registros)
                logger.info(
                    f"[SICAR/{estado}] Salvos: {_status['total_salvos']} | "
                    f"Ignorados: {_status['total_ignorados']}"
                )

    except Exception as exc:
        logger.error(f"Erro durante ingestão de {estado}: {exc}", exc_info=True)
        db.rollback()
        _status["erro"] = str(exc)
    finally:
        db.close()
        _status["rodando"] = False
        _status["concluido_em"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[SICAR/{estado}] Concluído — "
            f"salvos={_status['total_salvos']} ignorados={_status['total_ignorados']}"
        )
