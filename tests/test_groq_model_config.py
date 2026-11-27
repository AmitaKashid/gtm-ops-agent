import importlib
import pytest


MODULES = [
    'agents.lead_intelligence.nodes.research_company',
    'agents.lead_intelligence.nodes.score_lead',
    'agents.lead_intelligence.nodes.draft_email',
    'agents.email_triage.nodes.classify_email',
    'agents.email_triage.nodes.extract_context',
    'agents.email_triage.nodes.draft_reply',
    'agents.meeting_intelligence.nodes.extract_transcript',
    'agents.meeting_intelligence.nodes.extract_action_items',
    'agents.meeting_intelligence.nodes.generate_summary',
    'agents.competitor_intelligence.nodes.analyze_changes',
    'agents.hr_onboarding.nodes.parse_request',
    'agents.hr_onboarding.nodes.plan_provisioning',
]


@pytest.mark.parametrize('module_name', MODULES)
def test_groq_model_can_be_configured(module_name, monkeypatch):
    module = importlib.import_module(module_name)
    monkeypatch.setenv('DEFAULT_LLM_PROVIDER', 'groq')
    monkeypatch.setenv('GROQ_MODEL', 'example-model')
    monkeypatch.setattr(module, 'ChatGroq', lambda **kwargs: kwargs)
    assert module.get_llm()['model'] == 'example-model'
