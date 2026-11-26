import importlib
import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from api.main import app


def fake_model(text):
    return RunnableLambda(lambda _: AIMessage(content=text))


def test_meeting_produces_task_payload_with_stubbed_models(monkeypatch):
    transcript = importlib.import_module("agents.meeting_intelligence.nodes.extract_transcript")
    actions = importlib.import_module("agents.meeting_intelligence.nodes.extract_action_items")
    summary = importlib.import_module("agents.meeting_intelligence.nodes.generate_summary")
    monkeypatch.setattr(transcript, "get_llm", lambda: fake_model(
        "MEETING_TYPE: planning\nTOPICS_DISCUSSED: roadmap\n"
        "PARTICIPANTS_IDENTIFIED: Ahmed\nCLEANED_CONTENT: Ahmed will draft a plan."
    ))
    monkeypatch.setattr(actions, "get_llm", lambda: fake_model(
        'ACTION_ITEMS: [{"task": "Draft plan", "owner": "Ahmed", '
        '"deadline": null, "priority": "medium"}]\n'
        'DECISIONS_MADE: Draft a plan\nBLOCKERS_IDENTIFIED: NONE'
    ))
    monkeypatch.setattr(summary, "get_llm", lambda: fake_model(
        "SUMMARY: The team planned the roadmap.\nKEY_OUTCOMES: Draft plan\n"
        "NEXT_MEETING: NONE"
    ))
    with TestClient(app) as client:
        response = client.post("/meetings/analyze", json={
            "meeting_title": "Roadmap", "attendees": "Ahmed",
            "transcript": "Ahmed will draft a plan."
        })
    assert response.status_code == 200
    result = response.json()
    assert result["action_items_count"] == 1
    tasks = json.loads(result["notion_tasks_payload"])
    assert tasks[0]["title"] == "Draft plan"
    assert tasks[0]["assignee"] == "Ahmed"
    assert result["notifications_ready"] is True
