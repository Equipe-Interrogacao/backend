"""Cache em memória das propriedades lidas do KML CAR (MVP /app)."""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.car_kml_loader import load_car_gdf
from app.services.car_kml_parser import parse_description, point_lat_lon

logger = logging.getLogger(__name__)

# Raiz do serviço ingestao/ (onde ficam app/ e data/)
_SERVICE_ROOT = Path(__file__).resolve().parent.parent.parent
KML_PATH = _SERVICE_ROOT / "data" / "car_propriedades.kml"

_propriedades_list: list[dict] = []
_by_cod_car: dict[str, dict] = {}


def init_car_kml_store() -> None:
    """Carrega o KML na subida da aplicação. Exige rede se o KML for NetworkLink."""
    global _propriedades_list, _by_cod_car
    _propriedades_list = []
    _by_cod_car = {}

    if not KML_PATH.is_file():
        logger.warning("KML não encontrado em %s — endpoints /ingestao/car-kml/* vazios.", KML_PATH)
        return

    try:
        gdf = load_car_gdf(KML_PATH)
    except Exception:
        logger.exception("Falha ao carregar KML CAR em %s", KML_PATH)
        return

    for _, row in gdf.iterrows():
        cod_car, municipio = parse_description(row.get("description"))
        if not cod_car:
            continue
        lat, lon = point_lat_lon(row.geometry)
        if lat is None or lon is None:
            continue

        item = {
            "cod_car": cod_car,
            "municipio": municipio or "",
            "latitude": lat,
            "longitude": lon,
        }
        _propriedades_list.append(item)
        if cod_car not in _by_cod_car:
            _by_cod_car[cod_car] = item

    logger.info("CAR KML: %s propriedades em memória.", len(_propriedades_list))


def listar_kml() -> list[dict]:
    return list(_propriedades_list)


def buscar_kml(cod_car: str) -> dict | None:
    return _by_cod_car.get(cod_car)


def total_kml() -> int:
    return len(_propriedades_list)
