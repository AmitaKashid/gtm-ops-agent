import importlib
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from api.main import app


def success(content):
    return RunnableLambda(lambda _: AIMessage(content=content))


def failure():
    def fail(_):
        raise RuntimeError('private provider detail')
    return RunnableLambda(fail)


def test_model_failures_never_mark_lead_completed(monkeypatch):
    research = importlib.import_module('agents.lead_intelligence.nodes.research_company')
    score = importlib.import_module('agents.lead_intelligence.nodes.score_lead')
    draft = importlib.import_module('agents.lead_intelligence.nodes.draft_email')
    for failing in ('research', 'score', 'draft'):
        monkeypatch.setattr(research, 'get_llm', lambda: failure() if failing == 'research' else success('INDUSTRY: Technology\nSUMMARY: Analytics'))
        monkeypatch.setattr(score, 'get_llm', lambda: failure() if failing == 'score' else success('SCORE: HIGH\nIS_QUALIFIED: true'))
        monkeypatch.setattr(draft, 'get_llm', lambda: failure() if failing == 'draft' else success('SUBJECT: Hello\nBODY: Hello'))
        with TestClient(app) as client:
            response = client.post('/leads/analyze', json={'company_name': 'Example'})
        assert response.status_code == 200
        data = response.json()
        assert data['completed'] is False
        assert data['error']
        assert 'private provider detail' not in data['error']
        if failing != 'draft':
            assert data['draft_email_body'] is None
