"""Carrega feições a partir de um ficheiro KML (Placemarks ou NetworkLink + WMS)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import geopandas as gpd

KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


def _look_at_center(tree: Any) -> tuple[float, float]:
    for xpath in (
        ".//kml:NetworkLink/kml:LookAt",
        ".//kml:Document/kml:LookAt",
    ):
        look = tree.find(xpath, KML_NS)
        if look is None:
            continue
        lon_el = look.find("kml:longitude", KML_NS)
        lat_el = look.find("kml:latitude", KML_NS)
        lon_t = lon_el.text if lon_el is not None else None
        lat_t = lat_el.text if lat_el is not None else None
        if lon_t and lat_t and lon_t.strip() and lat_t.strip():
            return float(lon_t), float(lat_t)
    raise ValueError("KML sem LookAt com longitude/latitude.")


def _prepare_wms_href(href: str, lon: float, lat: float) -> str:
    href = href.replace("KMPLACEMARK:false", "KMPLACEMARK:true")
    href = re.sub(r"height=2048", "height=512", href, flags=re.I)
    href = re.sub(r"width=2048", "width=512", href, flags=re.I)
    delta = 0.12
    bbox = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"
    if "bbox=" not in href.lower():
        href = f"{href}{'&' if '?' in href else '?'}bbox={bbox}"
    return href


def load_car_gdf(path: Path) -> gpd.GeoDataFrame:
    """Lê o KML local. Se for só NetworkLink (sem Placemarks), obtém dados via URL WMS."""
    gdf = gpd.read_file(path, driver="KML")
    if len(gdf) > 0:
        return gdf

    tree = ET.parse(path)
    href_el = tree.find(".//kml:NetworkLink/kml:Url/kml:href", KML_NS)
    if href_el is None or href_el.text is None or not href_el.text.strip():
        raise ValueError(
            "KML sem Placemarks e sem NetworkLink/Url/href para obter dados."
        )

    lon, lat = _look_at_center(tree)
    href = _prepare_wms_href(href_el.text.strip(), lon, lat)
    return gpd.read_file(href, driver="KML")
