from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.controllers import imovel_controller
from app.models.imovel import Imovel


def test_buscar_400_formato_invalido():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        imovel_controller.buscar_imovel_por_car("x", db)
    assert exc.value.status_code == 400


def test_buscar_404():
    db = MagicMock()
    with patch.object(
        imovel_controller._service,
        "buscar_por_car",
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc:
            imovel_controller.buscar_imovel_por_car("35253000000167", db)
    assert exc.value.status_code == 404


def test_buscar_500_sqlalchemy():
    db = MagicMock()
    with patch.object(
        imovel_controller._service,
        "buscar_por_car",
        side_effect=SQLAlchemyError("db down"),
    ):
        with pytest.raises(HTTPException) as exc:
            imovel_controller.buscar_imovel_por_car("35253000000167", db)
    assert exc.value.status_code == 500


def test_buscar_200():
    db = MagicMock()
    imovel = Imovel(
        id=1,
        codigo_car="35253000000167",
        area_ha=5.0,
        municipio="JAÚ",
        situacao="Ativo",
        dt_inscricao=datetime(2020, 1, 1, tzinfo=timezone.utc),
        dt_analise=None,
        geometria=None,
    )
    with patch.object(
        imovel_controller._service,
        "buscar_por_car",
        return_value=imovel,
    ):
        out = imovel_controller.buscar_imovel_por_car("35253000000167", db)
    assert out.codigo_car == "35253000000167"
    assert out.area_ha == 5.0
    assert out.municipio == "JAÚ"
    assert out.situacao == "Ativo"
    assert out.dt_analise is None
