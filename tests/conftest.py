"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from codicecivico.api.app import app


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client for FastAPI (no DB required)."""
    return TestClient(app)
