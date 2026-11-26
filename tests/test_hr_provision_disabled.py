from fastapi.testclient import TestClient
from api.main import app


def test_provision_is_blocked_without_approval_implementation():
    with TestClient(app) as client:
        response = client.post("/hr/provision", json={"request_id": "example"})
    assert response.status_code == 503
    assert "disabled" in response.json()["detail"]
