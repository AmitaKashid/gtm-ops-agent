from fastapi.testclient import TestClient
from api.main import app


def test_scan_date_controls_deal_age():
    deal = {
        "deal_id": "D1", "deal_name": "Example", "company": "Example",
        "owner": "Amita", "stage": "Proposal", "deal_value": 1000,
        "contact_email": "test@example.com", "contact_phone": "123",
        "last_contact_date": "2026-01-01", "stage_changed_date": "2026-01-01",
    }
    with TestClient(app) as client:
        early = client.post("/crm/analyze", json={"deals": [deal], "scan_date": "2026-01-05"})
        late = client.post("/crm/analyze", json={"deals": [deal], "scan_date": "2026-02-05"})
    assert early.status_code == late.status_code == 200
    assert early.json()["problematic_deals_count"] == 0
    assert early.json()["total_alerts_count"] == 0
    assert late.json()["problematic_deals_count"] == 1
    assert late.json()["total_alerts_count"] == 2
    alerts = late.json()["owner_notifications"]["Amita"]["alerts"]
    assert next(a for a in alerts if a["alert_type"] == "stale")["days_inactive"] == 35


def test_invalid_scan_date_returns_422():
    with TestClient(app) as client:
        response = client.post("/crm/analyze", json={"deals": [], "scan_date": "2026-02-30"})
    assert response.status_code == 422
