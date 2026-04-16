"""
Serviço de ingestão DETER (INPE / TerraBrasilis).

Orquestra a busca paginada via WFS (deter-cerrado) e persiste no PostgreSQL + PostGIS
usando upsert idempotente por id_alerta.
Segue o mesmo padrão assíncrono de sicar_ingestao_service.py.
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

from app.clients.inpe_deter_client import buscar_alertas_por_estado
from app.models.alerta_deter import AlertaDeter

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
    """Converte geometria GeoJSON para WKBElement PostGIS (MULTIPOLYGON SRID 4326)."""
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
        logger.debug(f"[DETER] Falha ao converter geometria: {exc}")
        return None


def _parse_datetime(val) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


def _extrair_dados_feature(feature: dict, uf: str = "SP") -> Optional[dict]:
    """
    Mapeia os campos reais do WFS TerraBrasilis DETER para AlertaDeter.

    Campos confirmados na API (deter-cerrado-nb:deter_cerrado):
        classname      — classe do alerta (ex.: DESMATAMENTO_CR, DEGRADACAO)
        view_date      — data de detecção (YYYY-MM-DD)
        created_date   — data de publicação
        areamunkm      — área no município em km²
        areatotalkm    — área total em km²
        areauckm       — área em UC em km²
        uc             — nome da unidade de conservação
        uf             — sigla do estado (ex.: 'SP')
        municipality   — nome do município
        publish_month  — mês de publicação
    """
    props = feature.get("properties") or {}
    geom_json = feature.get("geometry")

    fid = feature.get("id") or str(props.get("gid") or props.get("ogc_fid") or "")
    if not fid or not geom_json:
        return None

    # Filtro defensivo: descartar registros fora do estado
    uf_api = (props.get("uf") or "").upper()
    if uf_api and uf_api != uf.upper():
        return None

    id_alerta = f"deter.{fid}"

    geometria = _converter_geometria(geom_json)
    if geometria is None:
        return None

    return {
        "id_alerta": id_alerta,
        "classname": props.get("classname"),
        "view_date": _parse_datetime(props.get("view_date")),
        "area_km2": props.get("areamunkm") or props.get("areatotalkm"),
        "uc": props.get("uc"),
        "uf": uf,
        "municipio": props.get("municipality") or props.get("municipali"),
        "bioma": props.get("biome") or props.get("bioma"),
        "geometria": geometria,
    }


def _dedup(registros: list[dict], chave: str) -> list[dict]:
    """Remove duplicatas dentro do mesmo batch pela chave única."""
    vistos: set = set()
    resultado = []
    for r in registros:
        v = r[chave]
        if v not in vistos:
            vistos.add(v)
            resultado.append(r)
    return resultado


def _upsert_batch(session, registros: list[dict]) -> None:
    registros = _dedup(registros, "id_alerta")
    if not registros:
        return
    stmt = insert(AlertaDeter).values(registros)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id_alerta"],
        set_={k: stmt.excluded[k] for k in registros[0] if k != "id_alerta"},
    )
    session.execute(stmt)
    session.commit()


# --------------------------------------------------------------------------- #
# Função principal — executada como BackgroundTask
# --------------------------------------------------------------------------- #

async def ingerir_estado(estado: str = "SP") -> None:
    global _status

    if _status["rodando"]:
        logger.warning("[DETER] Ingestão já está em execução. Ignorando nova chamada.")
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
        async for pagina in buscar_alertas_por_estado(estado):
            registros = []
            for feature in pagina:
                dados = _extrair_dados_feature(feature, uf=estado)
                if dados:
                    registros.append(dados)
                else:
                    _status["total_ignorados"] += 1

            if registros:
                _upsert_batch(db, registros)
                _status["total_salvos"] += len(registros)
                logger.info(
                    f"[DETER/{estado}] Salvos: {_status['total_salvos']} | "
                    f"Ignorados: {_status['total_ignorados']}"
                )

    except Exception as exc:
        logger.error(f"[DETER] Erro durante ingestão de {estado}: {exc}", exc_info=True)
        db.rollback()
        _status["erro"] = str(exc)
    finally:
        db.close()
        _status["rodando"] = False
        _status["concluido_em"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[DETER/{estado}] Concluído — "
            f"salvos={_status['total_salvos']} ignorados={_status['total_ignorados']}"
        )
