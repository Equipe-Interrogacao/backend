from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.controllers import banco_controller


def test_listar_ok():
    db = MagicMock()
    with patch.object(banco_controller.service, "listar_propriedades", return_value=[]):
        assert banco_controller.listar_propriedades(db) == []


def test_buscar_404():
    db = MagicMock()
    with patch.object(banco_controller.service, "buscar_por_id", return_value=None):
        with pytest.raises(HTTPException) as exc:
            banco_controller.buscar_propriedade(1, db)
    assert exc.value.status_code == 404


def test_buscar_ok():
    db = MagicMock()
    p = MagicMock()
    with patch.object(banco_controller.service, "buscar_por_id", return_value=p):
        assert banco_controller.buscar_propriedade(1, db) is p


def test_deletar_404():
    db = MagicMock()
    with patch.object(banco_controller.service, "deletar_propriedade", return_value=None):
        with pytest.raises(HTTPException) as exc:
            banco_controller.deletar_propriedade(1, db)
    assert exc.value.status_code == 404


def test_criar_ok():
    db = MagicMock()
    p = MagicMock()
    with patch.object(banco_controller.service, "criar_propriedade", return_value=p):
        assert banco_controller.criar_propriedade({"cod_car": "1"}, db) is p


def test_deletar_ok():
    db = MagicMock()
    p = MagicMock()
    with patch.object(banco_controller.service, "deletar_propriedade", return_value=p):
        out = banco_controller.deletar_propriedade(5, db)
    assert "5" in out["mensagem"]
