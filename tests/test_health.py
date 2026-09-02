from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_200() -> None:
    """The /health endpoint should be reachable and return HTTP 200."""
    response = client.get("/health")

    assert response.status_code == 200


def test_health_check_response_body() -> None:
    """The /health endpoint should report status 'ok' and echo the configured environment."""
    response = client.get("/health")
    body = response.json()

    assert body["status"] == "ok"
    assert body["environment"] == "development"
