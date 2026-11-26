import importlib

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from api.main import app


def test_competitor_comparison_with_stubbed_http_and_model(monkeypatch):
    scraper = importlib.import_module("agents.competitor_intelligence.nodes.scrape_competitors")
    analyzer = importlib.import_module("agents.competitor_intelligence.nodes.analyze_changes")

    async def fake_fetch_page(client, url):
        assert url.startswith("https://example.com")
        return "Plan price is 20 euros"

    monkeypatch.setattr(scraper, "fetch_page", fake_fetch_page)
    monkeypatch.setattr(scraper, "DELAY_BETWEEN_REQUESTS", 0)
    monkeypatch.setattr(analyzer, "get_llm", lambda: RunnableLambda(
        lambda _: AIMessage(content=(
            "CHANGES_DETECTED: true\nSIGNIFICANT_CHANGES: Price increased\n"
            "BUSINESS_IMPACT: Review pricing\nRECOMMENDED_ACTION: Compare plans"
        ))
    ))
    with TestClient(app) as client:
        response = client.post("/competitors/analyze", json={
            "competitors": [{"name": "Example", "url": "https://example.com",
                             "pages": ["/pricing"],
                             "previous_content": {"pricing": "Plan price was 10 euros"}}]
        })
    assert response.status_code == 200
    result = response.json()
    assert result["successful_scrapes"] == 1
    assert result["total_changes_found"] == 1
    assert result["competitor_analyses"][0]["changes_detected"] is True
    assert result["report_ready"] is True
