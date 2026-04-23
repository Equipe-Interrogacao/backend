"""
Serviço de ingestão de Unidades de Conservação (ICMBio / CNUC).
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

from app.clients.icmbio_client import buscar_ucs_por_estado
from app.models.unidade_conservacao import UnidadeConservacao

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
        logger.debug(f"[ICMBio] Falha ao converter geometria: {exc}")
        return None


def _extrair_dados_feature(feature: dict, uf: str = "SP") -> Optional[dict]:
    """
    Mapeia campos do WFS INDE/ICMBio (ICMBio:limiteucsfederais_a) para UnidadeConservacao.

    Campos confirmados (mar/2026):
        cnuc        — código CNUC único
        nomeuc      — nome da UC
        siglacateg  — sigla da categoria (APA, ESEC, PARNA, RESEX…)
        grupouc     — Proteção Integral / Uso Sustentável
        ufabrang    — UF(s) abrangidas (ex: 'SP' ou 'SP;MG')
        areahaalb   — área em hectares
    """
    props = feature.get("properties") or {}
    geom_json = feature.get("geometry")

    cod = (
        props.get("cnuc")
        or str(props.get("ogc_fid") or props.get("gid") or feature.get("id") or "")
    )
    if not cod or not geom_json:
        logger.debug(f"[ICMBio] Feature sem cod_uc ou geometria — props: {list(props.keys())}")
        return None

    geometria = _converter_geometria(geom_json)
    if geometria is None:
        return None

    return {
        "cod_uc": str(cod),
        "nome": props.get("nomeuc"),
        "categoria": props.get("siglacateg"),
        "grupo": props.get("grupouc"),
        "esfera": props.get("esfera"),
        "uf": props.get("ufabrang") or uf,
        "area_ha": props.get("areahaalb"),
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
    registros = _dedup(registros, "cod_uc")
    if not registros:
        return
    stmt = insert(UnidadeConservacao).values(registros)
    stmt = stmt.on_conflict_do_update(
        index_elements=["cod_uc"],
        set_={k: stmt.excluded[k] for k in registros[0] if k != "cod_uc"},
    )
    session.execute(stmt)
    session.commit()


async def ingerir_estado(uf: str = "SP") -> None:
    global _status

    if _status["rodando"]:
        logger.warning("[ICMBio] Ingestão já está em execução. Ignorando nova chamada.")
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
        async for pagina in buscar_ucs_por_estado(uf):
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
                    f"[ICMBio/{uf}] Salvos: {_status['total_salvos']} | "
                    f"Ignorados: {_status['total_ignorados']}"
                )

    except Exception as exc:
        logger.error(f"[ICMBio] Erro durante ingestão de {uf}: {exc}", exc_info=True)
        db.rollback()
        _status["erro"] = str(exc)
    finally:
        db.close()
        _status["rodando"] = False
        _status["concluido_em"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[ICMBio/{uf}] Concluído — "
            f"salvos={_status['total_salvos']} ignorados={_status['total_ignorados']}"
        )
