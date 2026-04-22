import json
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.passivo_ambiental_schema import FonteINPE, PassivoAmbiental

logger = logging.getLogger(__name__)

_TABELAS_CONFIG = {
    FonteINPE.deter: {
        "tabela": "alerta_deter",
        "coluna_classe": "classe",
        "coluna_data": "data_deteccao",
        "geom_type": "polygon",
    },
    FonteINPE.prodes: {
        "tabela": "desmatamento_prodes",
        "coluna_classe": "classe",
        "coluna_data": "ano_referencia",
        "geom_type": "polygon",
    },
    FonteINPE.queimadas: {
        "tabela": "foco_queimada",
        "coluna_classe": "satelite",
        "coluna_data": "data_hora",
        "geom_type": "point",
    },
}

_SQL_POLYGON = """
SELECT
    :fonte                                          AS fonte,
    t.{coluna_classe}                               AS tipo_alerta,
    t.{coluna_data}                                 AS data_referencia,
    ST_Area(
        ST_Intersection(
            t.geometria,
            ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
        )::geography
    ) / 10000                                       AS area_ha,
    ST_AsGeoJSON(
        ST_Intersection(
            t.geometria,
            ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
        )
    )                                               AS geometria_intersecao
FROM {tabela} t
WHERE ST_Intersects(
        t.geometria,
        ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
      )
  AND {filtro_data}
"""

_SQL_POINT = """
SELECT
    :fonte                                          AS fonte,
    t.{coluna_classe}                               AS tipo_alerta,
    t.{coluna_data}                                 AS data_referencia,
    0.0                                             AS area_ha,
    ST_AsGeoJSON(t.geometria)                       AS geometria_intersecao
FROM {tabela} t
WHERE ST_Intersects(
        t.geometria,
        ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)
      )
  AND {filtro_data}
"""


def _build_filtro_data(
    coluna_data: str,
    fonte: FonteINPE,
    data_inicio: Optional[date],
    data_fim: Optional[date],
) -> tuple[str, dict]:
    """Retorna (fragmento SQL, params extras) para o filtro temporal."""
    params: dict = {}

    if fonte == FonteINPE.prodes:
        ano_ini = data_inicio.year if data_inicio else 1988
        ano_fim = data_fim.year if data_fim else 2099
        return f"{coluna_data} BETWEEN :ano_ini AND :ano_fim", {
            "ano_ini": ano_ini,
            "ano_fim": ano_fim,
        }

    clauses = []
    if data_inicio:
        clauses.append(f"{coluna_data} >= :dt_ini")
        params["dt_ini"] = datetime.combine(data_inicio, datetime.min.time())
    if data_fim:
        clauses.append(f"{coluna_data} <= :dt_fim")
        params["dt_fim"] = datetime.combine(data_fim, datetime.max.time())

    filtro = " AND ".join(clauses) if clauses else "TRUE"
    return filtro, params


def cruzar_com_inpe(
    db: Session,
    geometria_geojson: dict,
    fontes: list[FonteINPE],
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
) -> list[PassivoAmbiental]:
    geojson_str = json.dumps(geometria_geojson)
    resultados: list[PassivoAmbiental] = []

    for fonte in fontes:
        cfg = _TABELAS_CONFIG[fonte]
        filtro_data, extra_params = _build_filtro_data(
            cfg["coluna_data"], fonte, data_inicio, data_fim,
        )

        template = _SQL_POINT if cfg["geom_type"] == "point" else _SQL_POLYGON
        sql = template.format(
            coluna_classe=cfg["coluna_classe"],
            coluna_data=cfg["coluna_data"],
            tabela=cfg["tabela"],
            filtro_data=filtro_data,
        )

        params = {"fonte": fonte.value, "geojson": geojson_str, **extra_params}

        try:
            rows = db.execute(text(sql), params).fetchall()
        except Exception:
            logger.exception("Erro na query espacial para fonte %s", fonte.value)
            continue

        for row in rows:
            data_ref = row.data_referencia
            if isinstance(data_ref, int):
                data_ref = date(data_ref, 1, 1)
            elif isinstance(data_ref, datetime):
                data_ref = data_ref.date()

            geom_inter = None
            if row.geometria_intersecao:
                try:
                    geom_inter = json.loads(row.geometria_intersecao)
                except (json.JSONDecodeError, TypeError):
                    pass

            resultados.append(
                PassivoAmbiental(
                    fonte=fonte,
                    tipo_alerta=row.tipo_alerta or "desconhecido",
                    data_referencia=data_ref,
                    area_ha=round(row.area_ha or 0.0, 4),
                    geometria_intersecao=geom_inter,
                )
            )

    return resultados
