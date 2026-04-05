"""Extrai cod_car, município e coordenadas a partir do KML / GeoDataFrame."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
from shapely.geometry.base import BaseGeometry


def parse_description(description: Any) -> tuple[str | None, str | None]:
    """Extrai Num_CAR e Municipio do HTML em `description`."""
    if description is None or (isinstance(description, float) and pd.isna(description)):
        return None, None
    text = str(description)
    num = re.search(r"Num_CAR</span>:</strong> <span[^>]*>([^<]+)", text)
    mun = re.search(r"Municipio</span>:</strong> <span[^>]*>([^<]+)", text)
    cod_car = num.group(1).strip() if num else None
    municipio = mun.group(1).strip() if mun else None
    return cod_car, municipio


def point_lat_lon(geometry: BaseGeometry | None) -> tuple[float | None, float | None]:
    """Point: lat=y, lon=x (EPSG:4326). Outros: centróide."""
    if geometry is None or geometry.is_empty:
        return None, None
    if geometry.geom_type == "Point":
        return float(geometry.y), float(geometry.x)
    c = geometry.centroid
    return float(c.y), float(c.x)
