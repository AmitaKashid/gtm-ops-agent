from contextlib import asynccontextmanager
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import app
from api.routers import workspace
from workspace_security.authorization import AccessDenied, Permission
from workspace_security.identity import VerifiedIdentity


class FakeConnection:
    def __init__(self):
        self.in_transaction = False

    @asynccontextmanager
    async def transaction(self):
        self.in_transaction = True
        try:
            yield
        finally:
            self.in_transaction = False


def test_sample_scan_checks_membership_and_runs_real_crm_graph(monkeypatch):
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    identity = VerifiedIdentity('https://identity.example', 'person')
    org = uuid4()
    conn = FakeConnection()
    seen = []

    async def fake_conn():
        yield conn

    async def membership(connection, verified, organization_id, permission):
        assert connection.in_transaction
        seen.append((verified, organization_id, permission))
        if organization_id != org:
            raise AccessDenied()

    monkeypatch.setattr(workspace, 'require_membership', membership)
    app.dependency_overrides[workspace.workspace_identity] = lambda: identity
    app.dependency_overrides[workspace.workspace_connection] = fake_conn
    try:
        with TestClient(app) as client:
            result = client.post(f'/workspace/organizations/{org}/crm/sample-scan')
            assert result.status_code == 200
            data = result.json()
            assert data['completed'] is True
            assert data['scan_date'] == date.today().isoformat()
            assert data['total_deals_count'] == data['problematic_deals_count'] == 1
            assert data['total_alerts_count'] == 3
            assert seen == [(identity, org, Permission.READ)]
            assert client.post(f'/workspace/organizations/{uuid4()}/crm/sample-scan').status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_sample_scan_requires_authentication(monkeypatch):
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    with TestClient(app) as client:
        assert client.post(f'/workspace/organizations/{uuid4()}/crm/sample-scan').status_code == 401
