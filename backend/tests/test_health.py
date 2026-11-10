from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_ok():
    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is False
