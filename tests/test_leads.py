import importlib

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from api.main import app


def fake_model(text):
    return RunnableLambda(lambda _: AIMessage(content=text))


def test_lead_analysis_with_stubbed_models(monkeypatch):
    research = importlib.import_module("agents.lead_intelligence.nodes.research_company")
    scoring = importlib.import_module("agents.lead_intelligence.nodes.score_lead")
    drafting = importlib.import_module("agents.lead_intelligence.nodes.draft_email")
    monkeypatch.setattr(research, "get_llm", lambda: fake_model(
        "COMPANY_SIZE: 150\nINDUSTRY: Technology\nDESCRIPTION: Software company\n"
        "SUMMARY: Interested in analytics"
    ))
    monkeypatch.setattr(scoring, "get_llm", lambda: fake_model(
        "SCORE: HIGH\nREASONING: Relevant analytics need\nIS_QUALIFIED: true"
    ))
    monkeypatch.setattr(drafting, "get_llm", lambda: fake_model(
        "SUBJECT: Analytics discussion\nBODY: Hello, let us discuss your needs."
    ))
    with TestClient(app) as client:
        response = client.post("/leads/analyze", json={
            "company_name": " Example Corp ", "message": "Need analytics"
        })
    assert response.status_code == 200
    result = response.json()
    assert result["company_name"] == "Example Corp"
    assert result["score"] == "HIGH"
    assert result["is_qualified"] is True
    assert result["draft_email_subject"] == "Analytics discussion"
    assert result["completed"] is True
