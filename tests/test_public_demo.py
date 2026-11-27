from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.public_demo import PublicDemoMiddleware


def make_client(monkeypatch, enabled):
    monkeypatch.setenv("PUBLIC_DEMO", enabled)
    app = FastAPI()
    app.add_middleware(PublicDemoMiddleware)

    @app.post("/{path:path}")
    async def post(path: str):
        return {"path": path}

    return TestClient(app)


def test_public_demo_disables_hr_and_competitor_requests(monkeypatch):
    client = make_client(monkeypatch, "true")
    assert client.post("/hr/onboard", json={}).status_code == 503
    assert client.post("/competitors/analyze", json={}).status_code == 503
    assert client.post("/leads/analyze", json={}).status_code == 200


def test_local_mode_keeps_existing_routes_available(monkeypatch):
    client = make_client(monkeypatch, "false")
    assert client.post("/competitors/analyze", json={}).status_code == 200


def test_public_demo_limits_large_requests(monkeypatch):
    client = make_client(monkeypatch, "true")
    assert client.post("/leads/analyze", content=b"x" * 32769).status_code == 413


def test_public_demo_limits_requests(monkeypatch):
    client = make_client(monkeypatch, "true")
    for _ in range(60):
        assert client.post("/leads/analyze", json={}).status_code == 200
    assert client.post("/leads/analyze", json={}).status_code == 429
