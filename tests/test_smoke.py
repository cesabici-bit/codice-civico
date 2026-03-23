"""M3: Smoke test E2E — verify the API starts and responds.

This is the first test written (Smoke Before Unit).
It produces human-readable output and becomes the L4 golden snapshot.
"""

from fastapi.testclient import TestClient

from codicecivico.api.app import app


def test_health_endpoint_returns_ok() -> None:
    """Smoke test: /api/v1/health responds with status ok.

    # SOURCE: FastAPI docs — TestClient usage
    # https://fastapi.tiangolo.com/tutorial/testing/
    """
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    # Human-readable output
    print("\n=== SMOKE TEST OUTPUT ===")
    print(f"Health: {data}")
    print(f"Version: {data['version']}")
    print("=========================\n")


def test_openapi_docs_available() -> None:
    """Smoke test: OpenAPI docs are accessible."""
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200


def test_all_route_groups_registered() -> None:
    """Smoke test: all expected route prefixes are registered."""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()
    paths = list(openapi["paths"].keys())

    expected_prefixes = [
        "/api/v1/health",
        "/api/v1/politicians",
        "/api/v1/contracts",
        "/api/v1/courts",
        "/api/v1/laws",
        "/api/v1/magistrates",
        "/api/v1/dossier",
        "/api/v1/search",
    ]
    for prefix in expected_prefixes:
        assert any(p.startswith(prefix) for p in paths), f"Missing route prefix: {prefix}"

    # Human-readable output
    print("\n=== REGISTERED ROUTES ===")
    for p in sorted(paths):
        print(f"  {p}")
    print("=========================\n")
