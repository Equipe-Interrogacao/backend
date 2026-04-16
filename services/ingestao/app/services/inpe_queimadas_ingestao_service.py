"""
Serviço de ingestão BDQueimadas (INPE).

Orquestra a busca paginada da API REST do BDQueimadas e persiste no
PostgreSQL + PostGIS usando upsert idempotente por id_foco.
Segue o mesmo padrão assíncrono de sicar_ingestao_service.py.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from app.clients.inpe_queimadas_client import (
    QUEIMADAS_ANO_DEFAULT,
    buscar_focos_por_estado,
)
from app.models.foco_queimada import FocoQueimada

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

def _converter_geometria_ponto(lat: Optional[float], lon: Optional[float]) -> Optional[object]:
    """Converte lat/lon para WKBElement PostGIS (POINT SRID 4326)."""
    if lat is None or lon is None:
        return None
    try:
        geom = Point(lon, lat)  # shapely: (x=lon, y=lat)
        if geom.is_empty:
            return None
        return from_shape(geom, srid=4326)
    except Exception as exc:
        logger.debug(f"[Queimadas] Falha ao converter geometria ponto: {exc}")
        return None


def _parse_datetime(val) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_float(val) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _extrair_dados_foco(feature: dict, estado: str = "SP") -> Optional[dict]:
    """
    Mapeia os campos de um feature GeoJSON WFS BDQueimadas para o modelo FocoQueimada.

    Campos confirmados na API (dados_abertos:focos_{ano}_br_satref):
        id_foco_bdq   — identificador único do foco
        foco_id       — UUID alternativo
        latitude / longitude — coordenadas
        data_hora_gmt — data e hora UTC de detecção
        satelite      — satélite detector
        municipio     — município (caixa-alta)
        estado        — nome do estado em caixa-alta (ex.: 'SÃO PAULO')
        pais          — país
        bioma         — bioma
        frp           — Fire Radiative Power (MW)
    """
    # Suporta tanto feature GeoJSON (com 'properties') quanto dict plano
    if "properties" in feature:
        props = feature.get("properties") or {}
        geom_json = feature.get("geometry")
        fid = str(props.get("id_foco_bdq") or props.get("foco_id") or feature.get("id") or "")
    else:
        props = feature
        geom_json = None
        fid = str(props.get("id_foco_bdq") or props.get("id") or props.get("id_foco") or "")

    if not fid:
        return None

    id_foco = f"queimadas.{fid}"

    lat = _parse_float(props.get("latitude") or props.get("lat"))
    lon = _parse_float(props.get("longitude") or props.get("lon"))

    # Prefer WFS geometry; fall back to lat/lon fields
    if geom_json and geom_json.get("type") == "Point":
        coords = geom_json.get("coordinates", [])
        if len(coords) >= 2:
            lon = lon if lon is not None else _parse_float(coords[0])
            lat = lat if lat is not None else _parse_float(coords[1])

    geometria = _converter_geometria_ponto(lat, lon)
    if geometria is None:
        return None

    return {
        "id_foco": id_foco,
        "data_hora_gmt": _parse_datetime(props.get("data_hora_gmt") or props.get("datahora")),
        "latitude": lat,
        "longitude": lon,
        "satelite": props.get("satelite") or props.get("satellite"),
        "municipio": props.get("municipio") or props.get("municipality"),
        "estado": estado,
        "pais": props.get("pais") or props.get("country") or "Brasil",
        "bioma": props.get("bioma") or props.get("biome"),
        "frp": _parse_float(props.get("frp")),
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
    registros = _dedup(registros, "id_foco")
    if not registros:
        return
    stmt = insert(FocoQueimada).values(registros)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id_foco"],
        set_={k: stmt.excluded[k] for k in registros[0] if k != "id_foco"},
    )
    session.execute(stmt)
    session.commit()


# --------------------------------------------------------------------------- #
# Função principal — executada como BackgroundTask
# --------------------------------------------------------------------------- #

async def ingerir_estado(
    estado: str = "SP",
    ano_inicio: int = 2016,
    ano_fim: int = QUEIMADAS_ANO_DEFAULT,
) -> None:
    global _status

    if _status["rodando"]:
        logger.warning("[Queimadas] Ingestão já está em execução. Ignorando nova chamada.")
        return

    anos = list(range(ano_inicio, ano_fim + 1))

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
        for ano in anos:
            logger.info(f"[Queimadas/{estado}] Iniciando ano {ano} ...")
            async for pagina in buscar_focos_por_estado(estado, ano):
                registros = []
                for foco in pagina:
                    dados = _extrair_dados_foco(foco, estado=estado)
                    if dados:
                        registros.append(dados)
                    else:
                        _status["total_ignorados"] += 1

                if registros:
                    _upsert_batch(db, registros)
                    _status["total_salvos"] += len(registros)
                    logger.info(
                        f"[Queimadas/{estado}/{ano}] Salvos: {_status['total_salvos']} | "
                        f"Ignorados: {_status['total_ignorados']}"
                    )

    except Exception as exc:
        logger.error(f"[Queimadas] Erro durante ingestão de {estado}: {exc}", exc_info=True)
        db.rollback()
        _status["erro"] = str(exc)
    finally:
        db.close()
        _status["rodando"] = False
        _status["concluido_em"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[Queimadas/{estado}] Concluído — "
            f"salvos={_status['total_salvos']} ignorados={_status['total_ignorados']}"
        )
