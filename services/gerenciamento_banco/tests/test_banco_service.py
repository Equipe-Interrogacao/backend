from unittest.mock import MagicMock

from app.models.propriedade import Propriedade
from app.services.banco_service import BancoService


def test_listar_vazio():
    db = MagicMock()
    db.query.return_value.all.return_value = []
    assert BancoService().listar_propriedades(db) == []


def test_buscar_por_id():
    p = MagicMock()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = p
    assert BancoService().buscar_por_id(db, 1) is p
    db.query.assert_called_once_with(Propriedade)


def test_criar_propriedade():
    db = MagicMock()
    dados = {
        "cod_car": "35253000000167",
        "nome_proprietario": "X",
        "municipio": "JAÚ",
        "estado": "SP",
        "area_total_ha": 1.0,
    }
    svc = BancoService()
    svc.criar_propriedade(db, dados)
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_deletar_propriedade_encontrada():
    db = MagicMock()
    p = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = p
    out = BancoService().deletar_propriedade(db, 1)
    assert out is p
    db.delete.assert_called_once_with(p)
    db.commit.assert_called_once()


def test_deletar_propriedade_nao_encontrada():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    assert BancoService().deletar_propriedade(db, 99) is None
    db.delete.assert_not_called()
