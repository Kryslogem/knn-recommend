from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


def test_health_ok_without_model(tmp_path):
    s = Settings(database_url=f"sqlite:///{(tmp_path / 't.db').as_posix()}", artifacts_dir=str(tmp_path / "none"))
    with TestClient(create_app(s)) as client:
        resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok" and body["model_loaded"] is False
