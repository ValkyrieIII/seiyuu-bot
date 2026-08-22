from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"


def test_docker_healthcheck_uses_stdlib_probe_and_health_endpoint():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "urllib.request" in dockerfile
    assert "http://127.0.0.1:8080/health" in dockerfile
    assert "import requests" not in dockerfile


def test_health_endpoint_returns_200():
    health_module_path = BACKEND_ROOT / "bot" / "health.py"
    assert health_module_path.exists(), "health route module is missing"

    sys.path.insert(0, str(BACKEND_ROOT))
    from bot.health import register_health_route

    app = FastAPI()
    register_health_route(SimpleNamespace(server_app=app))

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
