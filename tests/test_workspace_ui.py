from fastapi.testclient import TestClient
from api.main import app


def test_workspace_ui_is_disabled_in_public_demo(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.setenv('PUBLIC_DEMO', 'true')
    client = TestClient(app)
    assert client.get('/workspace-app').status_code == 404
    assert client.get('/workspace-app.js').status_code == 404


def test_workspace_ui_is_available_when_enabled_locally(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    client = TestClient(app)
    assert client.get('/workspace-app').status_code == 200
    assert client.get('/workspace-app.js').status_code == 200
