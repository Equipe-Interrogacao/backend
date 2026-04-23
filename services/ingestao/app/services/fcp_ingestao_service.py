"""
Serviço de ingestão de Territórios Quilombolas (FCP / INCRA).
Padrão idêntico ao inpe_deter_ingestao_service.py.
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

from app.clients.fcp_client import buscar_quilombolas_por_estado
from app.models.quilombola import Quilombola

logger = logging.getLogger(__name__)

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
        logger.debug(f"[FCP] Falha ao converter geometria: {exc}")
        return None


def _parse_datetime(val) -> Optional[datetime]:
    if not val:
        return None
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _extrair_dados_feature(feature: dict, uf: str = "SP") -> Optional[dict]:
    """
    Mapeia campos do SIPAM (painel_do_fogo:area_quilombola) para Quilombola.

    Campos confirmados:
        cd_quilomb  — código numérico único
        nr_process  — número de processo
        nm_comunid  — nome da comunidade
        nm_municip  — município
        cd_uf       — sigla do estado
        nr_area_ha  — área em hectares
        area_calc_  — área calculada
        fase        — fase (TITULO PARCIAL, DECRETO, etc.)
        dt_publica  — data de publicação (dd/mm/yyyy)
    """
    props = feature.get("properties") or {}
    geom_json = feature.get("geometry")

    cod = (
        str(props.get("cd_quilomb") or "")
        or props.get("nr_process")
        or str(feature.get("id") or "")
    )
    if not cod or not geom_json:
        logger.debug(f"[FCP] Feature sem cod_quilombola ou geometria — props: {list(props.keys())}")
        return None

    geometria = _converter_geometria(geom_json)
    if geometria is None:
        return None

    area = props.get("area_calc_") or props.get("nr_area_ha")
    try:
        area = float(area) if area is not None else None
    except (ValueError, TypeError):
        area = None

    return {
        "cod_quilombola": str(cod),
        "nome": props.get("nm_comunid"),
        "etnia": None,
        "municipio": props.get("nm_municip"),
        "uf": props.get("cd_uf") or uf,
        "area_ha": area,
        "fase": props.get("fase"),
        "dt_publicacao": _parse_datetime(props.get("dt_publica")),
        "geometria": geometria,
    }


def _dedup(registros: list[dict], chave: str) -> list[dict]:
    vistos: set = set()
    resultado = []
    for r in registros:
        v = r[chave]
        if v not in vistos:
            vistos.add(v)
            resultado.append(r)
    return resultado


def _upsert_batch(session, registros: list[dict]) -> None:
    registros = _dedup(registros, "cod_quilombola")
    if not registros:
        return
    stmt = insert(Quilombola).values(registros)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cod_quilombola"],
        set_={k: stmt.excluded[k] for k in registros[0] if k != "cod_quilombola"},
    )
    session.execute(stmt)
    session.commit()


async def ingerir_estado(uf: str = "SP") -> None:
    global _status

    if _status["rodando"]:
        logger.warning("[FCP] Ingestão já está em execução. Ignorando nova chamada.")
        return

    _status = {
        "rodando": True,
        "estado": uf,
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
        async for pagina in buscar_quilombolas_por_estado(uf):
            registros = []
            for feature in pagina:
                dados = _extrair_dados_feature(feature, uf=uf)
                if dados:
                    registros.append(dados)
                else:
                    _status["total_ignorados"] += 1

            if registros:
                _upsert_batch(db, registros)
                _status["total_salvos"] += len(registros)
                logger.info(
                    f"[FCP/{uf}] Salvos: {_status['total_salvos']} | "
                    f"Ignorados: {_status['total_ignorados']}"
                )

    except Exception as exc:
        logger.error(f"[FCP] Erro durante ingestão de {uf}: {exc}", exc_info=True)
        db.rollback()
        _status["erro"] = str(exc)
    finally:
        db.close()
        _status["rodando"] = False
        _status["concluido_em"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[FCP/{uf}] Concluído — "
            f"salvos={_status['total_salvos']} ignorados={_status['total_ignorados']}"
        )
