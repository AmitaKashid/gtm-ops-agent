import importlib

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from api.main import app


def test_spam_skips_context_and_draft(monkeypatch):
    classification = importlib.import_module("agents.email_triage.nodes.classify_email")
    context = importlib.import_module("agents.email_triage.nodes.extract_context")
    draft = importlib.import_module("agents.email_triage.nodes.draft_reply")
    called = []
    monkeypatch.setattr(classification, "get_llm", lambda: RunnableLambda(
        lambda _: AIMessage(content=(
            "CLASSIFICATION: SPAM\nPRIORITY: LOW\nSENTIMENT: NEUTRAL\n"
            "REASONING: Unsolicited promotion"
        ))
    ))
    monkeypatch.setattr(context, "get_llm", lambda: called.append("context"))
    monkeypatch.setattr(draft, "get_llm", lambda: called.append("draft"))
    with TestClient(app) as client:
        response = client.post("/emails/triage", json={
            "sender_email": "bot@example.com", "body": "Claim a prize"
        })
    assert response.status_code == 200
    result = response.json()
    assert result["classification"] == "SPAM"
    assert result["route_to"] == "ignore"
    assert result["draft_reply_body"] is None
    assert result["completed"] is True
    assert called == []
