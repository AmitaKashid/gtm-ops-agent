from fastapi.testclient import TestClient

from api.main import app


def test_backend_serves_dashboard_and_config():
    client = TestClient(app)
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "text/html" in dashboard.headers["content-type"]
    assert "GTM Ops Agent" in dashboard.text
    config = client.get("/api-config.js")
    assert config.status_code == 200
    assert "window.GTM_API_URL" in config.text
