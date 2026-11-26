import importlib
import json
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from api.main import app


class FakeModel:
    def __init__(self, payload):
        self.payload = payload

    def invoke(self, _prompt):
        return AIMessage(content=json.dumps(self.payload))


def test_onboarding_plan_without_external_services(monkeypatch):
    parser = importlib.import_module("agents.hr_onboarding.nodes.parse_request")
    planner = importlib.import_module("agents.hr_onboarding.nodes.plan_provisioning")
    router = importlib.import_module("api.routers.hr_onboarding")
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.setattr(parser, "get_llm", lambda: FakeModel({
        "employee_name": "Test Person", "employee_email": "test@example.com",
        "role": "Engineer", "department": "Engineering"
    }))
    monkeypatch.setattr(planner, "get_llm", lambda: FakeModel({
        "systems_to_provision": ["Slack"], "slack_channels": ["#general"],
        "requires_github": True, "requires_figma": False,
        "provisioning_plan_summary": "Review access"
    }))
    save = AsyncMock(return_value=True)
    monkeypatch.setattr(router, "save_onboarding_state", save)
    with TestClient(app) as client:
        response = client.post("/hr/onboard", json={
            "onboarding_request": "Onboard Test Person as Engineer"
        })
    assert response.status_code == 200
    result = response.json()
    assert result["employee_name"] == "Test Person"
    assert result["systems_to_provision"] == ["Slack"]
    assert result["approval_sent"] is False
    save.assert_awaited_once()
