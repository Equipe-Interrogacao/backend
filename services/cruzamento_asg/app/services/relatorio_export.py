"""
Exportação GPKG (OGC Geopackage) e GeoJSON (RFC 7946) a partir de dados brutos do relatório.
Nomes de camada centralizados para alinhamento com o time.
"""

from __future__ import annotations

import tempfile
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry

LAYER_IMOVEL_CAR = "imovel_car"
LAYER_PRODES = "prodes"
LAYER_DETER = "deter"
LAYER_FOCOS_QUEIMADA = "focos_queimada"
LAYER_AP = "areas_protegidas"


def _geom_from_geojson(g: Any) -> BaseGeometry | None:
    if not g or not isinstance(g, dict):
        return None
    try:
        return shape(g)
    except Exception:
        return None


def _gdf_from_features(
    rows: list[dict[str, Any]],
    geom_key: str = "geometria",
) -> gpd.GeoDataFrame:
    geoms: list[BaseGeometry | None] = []
    props: list[dict[str, Any]] = []
    for row in rows:
        geom = _geom_from_geojson(row.get(geom_key))
        p = {k: v for k, v in row.items() if k != geom_key}
        geoms.append(geom)
        props.append(p)
    if not rows:
        gser = gpd.GeoSeries([], dtype="geometry", crs="EPSG:4326")
        return gpd.GeoDataFrame(geometry=gser, crs="EPSG:4326")
    dfp = pd.DataFrame(props)
    gdf = gpd.GeoDataFrame(dfp, geometry=geoms, crs="EPSG:4326")
    return gdf


def _imovel_gdf(imovel: dict[str, Any] | None) -> gpd.GeoDataFrame:
    if not imovel or not imovel.get("geometria"):
        return gpd.GeoDataFrame(
            {"cod_imovel": []},
            geometry=gpd.GeoSeries([], dtype=object),
            crs="EPSG:4326",
        )
    g = _geom_from_geojson(imovel.get("geometria"))
    if g is None:
        return gpd.GeoDataFrame(geometry=gpd.GeoSeries([], dtype=object), crs="EPSG:4326")
    return gpd.GeoDataFrame(
        {
            "cod_imovel": [imovel.get("cod_imovel")],
            "uf": [imovel.get("uf")],
            "municipio": [imovel.get("municipio")],
            "status_imovel": [imovel.get("status_imovel")],
            "area_ha": [imovel.get("area")],
        },
        geometry=[g],
        crs="EPSG:4326",
    )


def montar_gpkg(
    imovel: dict[str, Any] | None,
    prodes: list[dict[str, Any]],
    deter: list[dict[str, Any]],
    focos: list[dict[str, Any]],
    ap: list[dict[str, Any]],
) -> bytes:
    layers: list[tuple[str, gpd.GeoDataFrame]] = [
        (LAYER_IMOVEL_CAR, _imovel_gdf(imovel)),
        (LAYER_PRODES, _gdf_from_features(prodes)),
        (LAYER_DETER, _gdf_from_features(deter)),
        (LAYER_FOCOS_QUEIMADA, _gdf_from_features(focos)),
        (LAYER_AP, _gdf_from_features(ap)),
    ]
    with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=True) as tmp:
        path = tmp.name
        for i, (name, gdf) in enumerate(layers):
            mode = "w" if i == 0 else "a"
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326", allow_empty=True)
            gdf.to_file(path, layer=name, driver="GPKG", mode=mode, engine="pyogrio")
        with open(path, "rb") as f:
            return f.read()


def _jsonable_val(v: Any) -> Any:
    if hasattr(v, "isoformat") and callable(v.isoformat):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _jsonable_val(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable_val(x) for x in v]
    return v


def _feature(geom: BaseGeometry, props: dict[str, Any], layer: str) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": mapping(geom),
        "properties": {**_jsonable_val(props), "camada": layer},
    }


def montar_geojson(
    imovel: dict[str, Any] | None,
    prodes: list[dict[str, Any]],
    deter: list[dict[str, Any]],
    focos: list[dict[str, Any]],
    ap: list[dict[str, Any]],
) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    if imovel and imovel.get("geometria"):
        g = _geom_from_geojson(imovel["geometria"])
        if g is not None:
            props = {k: v for k, v in imovel.items() if k != "geometria"}
            features.append(_feature(g, props, LAYER_IMOVEL_CAR))
    for row in prodes:
        g = _geom_from_geojson(row.get("geometria"))
        if g is not None:
            p = {k: v for k, v in row.items() if k != "geometria"}
            features.append(_feature(g, p, LAYER_PRODES))
    for row in deter:
        g = _geom_from_geojson(row.get("geometria"))
        if g is not None:
            p = {k: v for k, v in row.items() if k != "geometria"}
            features.append(_feature(g, p, LAYER_DETER))
    for row in focos:
        g = _geom_from_geojson(row.get("geometria"))
        if g is not None:
            p = {k: v for k, v in row.items() if k != "geometria"}
            features.append(_feature(g, p, LAYER_FOCOS_QUEIMADA))
    for row in ap:
        gk = "geometria" if "geometria" in row else "geometry"
        g = _geom_from_geojson(row.get(gk))
        if g is not None:
            p = {k: v for k, v in row.items() if k not in (gk,)}
            features.append(_feature(g, p, LAYER_AP))
    return {"type": "FeatureCollection", "features": features}
