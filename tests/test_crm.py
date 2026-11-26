from datetime import date, timedelta

from fastapi.testclient import TestClient
from api.main import app


def test_crm_counts_distinct_deals_and_individual_issues():
    today = date.today()
    old = (today - timedelta(days=61)).isoformat()
    problematic = {
        "deal_id": "DEMO-001", "deal_name": "Example deal",
        "company": "Example", "owner": "Ahmed", "stage": "Proposal",
        "deal_value": 15000, "contact_email": "contact@example.com",
        "contact_phone": None, "last_contact_date": old,
        "stage_changed_date": old,
    }
    healthy = {
        **problematic, "deal_id": "DEMO-002", "deal_name": "Healthy deal",
        "contact_phone": "+490000000000",
        "last_contact_date": today.isoformat(),
        "stage_changed_date": today.isoformat(),
    }
    with TestClient(app) as client:
        response = client.post("/crm/analyze", json={
            "deals": [problematic, healthy], "scan_date": today.isoformat()
        })
    assert response.status_code == 200
    data = response.json()
    assert data["error"] is None
    assert data["completed"] is True
    assert data["total_deals_count"] == 2
    assert data["healthy_deals_count"] == 1
    assert data["problematic_deals_count"] == 1
    assert data["total_alerts_count"] == 3
    notification = data["owner_notifications"]["Ahmed"]
    assert notification["alert_count"] == 3
    assert "*3 issue(s)* needing attention" in notification["message"]
    assert {a["deal_id"] for a in notification["alerts"]} == {"DEMO-001"}
    assert {a["alert_type"] for a in notification["alerts"]} == {
        "stale", "incomplete", "stuck"
    }
