from fastapi.testclient import TestClient
from api.main import allowed_origins, app


def test_configured_origins_are_trimmed(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com, http://localhost:8080, ")
    assert allowed_origins() == ["https://example.com", "http://localhost:8080"]


def test_local_origin_preflight():
    with TestClient(app) as client:
        response = client.options("/crm/analyze", headers={
            "Origin": "http://127.0.0.1:8080",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8080"


def test_workspace_preflight_allows_authorization_header():
    with TestClient(app) as client:
        response = client.options('/workspace/organizations/00000000-0000-0000-0000-000000000001/accounts', headers={
            'Origin': 'http://127.0.0.1:8080',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'authorization',
        })
    assert response.status_code == 200
    assert 'authorization' in response.headers['access-control-allow-headers'].lower()
