"""
Configuração de testes para o serviço de ingestão.
Desabilita create_all no Postgres via SKIP_DB_INIT.
"""

import os

os.environ.setdefault("SKIP_DB_INIT", "1")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/asg_db"
)

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.config.database import get_db
from app.main import app


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_db: MagicMock):
    def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
