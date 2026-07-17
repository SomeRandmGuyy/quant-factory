"""API test fixtures."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# Point env at fixture data BEFORE importing app modules that load settings
_FIXTURES = Path(__file__).resolve().parents[2] / "core" / "tests" / "fixtures" / "sample_prices"
os.environ["CSV_DATA_DIR"] = str(_FIXTURES)
os.environ["FUNDAMENTALS_FILE"] = str(_FIXTURES / "fundamentals.csv")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from fastapi.testclient import TestClient

# Re-import settings after env set — modules may already cache settings
from quant_lab_api import config as config_mod
from quant_lab_api.config import Settings

config_mod.settings = Settings()

from quant_lab_api.database import base as db_base
from quant_lab_api.database.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Rebuild engine for in-memory sqlite shared across connections
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
db_base.engine = _engine
db_base.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base.metadata.create_all(bind=_engine)

from quant_lab_api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fixtures_dir() -> Path:
    return _FIXTURES
