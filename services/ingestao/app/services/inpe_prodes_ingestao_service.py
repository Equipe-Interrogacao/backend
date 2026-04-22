"""
Serviço de ingestão PRODES (INPE / TerraBrasilis).

Orquestra a busca paginada via WFS e persiste no PostgreSQL + PostGIS
usando upsert idempotente por id_poligono.
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

from app.clients.inpe_prodes_client import buscar_desmatamento_por_estado
from app.models.desmatamento_prodes import DesmatamentoProdes

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
        logger.debug(f"[PRODES] Falha ao converter geometria: {exc}")
        return None


def _parse_int(val) -> Optional[int]:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _extrair_dados_feature(feature: dict, uf: str = "SP") -> Optional[dict]:
    """
    Mapeia os campos reais do WFS TerraBrasilis PRODES para DesmatamentoProdes.

    Campos confirmados na API (prodes-cerrado-nb:yearly_deforestation):
        uid        — id numérico do polígono
        year       — ano de referência
        area_km    — área em km²
        class_name — classe (ex.: 'd2023')
        main_class — classe principal (ex.: 'desmatamento')
        state      — nome do estado em caixa-alta (ex.: 'SÃO PAULO')
        path_row   — cena do satélite
        satellite  — satélite
    """
    props = feature.get("properties") or {}
    geom_json = feature.get("geometry")

    # ID estável: uid nas properties ou id do feature GeoJSON
    uid = props.get("uid") or props.get("gid") or props.get("ogc_fid")
    fid = str(uid) if uid else feature.get("id", "")
    if not fid or not geom_json:
        return None

    # Filtro defensivo: descartar registros fora do estado
    state_api = (props.get("state") or "").upper()
    if state_api and uf.upper() == "SP" and "PAULO" not in state_api:
        return None

    id_poligono = f"prodes.{fid}"

    geometria = _converter_geometria(geom_json)
    if geometria is None:
        return None

    return {
        "id_poligono": id_poligono,
        "ano": _parse_int(props.get("year")),
        "area_km2": props.get("area_km") or props.get("areakm"),
        "classname": props.get("class_name") or props.get("main_class"),
        "estado": props.get("state") or "SÃO PAULO",
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
    registros = _dedup(registros, "id_poligono")
    if not registros:
        return
    stmt = insert(DesmatamentoProdes).values(registros)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id_poligono"],
        set_={k: stmt.excluded[k] for k in registros[0] if k != "id_poligono"},
    )
    session.execute(stmt)
    session.commit()


# --------------------------------------------------------------------------- #
# Função principal — executada como BackgroundTask
# --------------------------------------------------------------------------- #

async def ingerir_estado(estado: str = "SP", nome_estado: str = "SÃO PAULO") -> None:
    global _status

    if _status["rodando"]:
        logger.warning("[PRODES] Ingestão já está em execução. Ignorando nova chamada.")
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
        async for pagina in buscar_desmatamento_por_estado(estado, nome_estado):
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
                    f"[PRODES/{estado}] Salvos: {_status['total_salvos']} | "
                    f"Ignorados: {_status['total_ignorados']}"
                )

    except Exception as exc:
        logger.error(f"[PRODES] Erro durante ingestão de {estado}: {exc}", exc_info=True)
        db.rollback()
        _status["erro"] = str(exc)
    finally:
        db.close()
        _status["rodando"] = False
        _status["concluido_em"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[PRODES/{estado}] Concluído — "
            f"salvos={_status['total_salvos']} ignorados={_status['total_ignorados']}"
        )
