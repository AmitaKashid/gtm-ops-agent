from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import app
from api.routers import workspace
from workspace_security.authorization import AccessDenied
from workspace_security.identity import VerifiedIdentity


def test_deal_routes_validate_and_scan_only_authorized_records(monkeypatch):
    org, other, account, deal_id = uuid4(), uuid4(), uuid4(), uuid4()
    identity = VerifiedIdentity('https://identity.example', 'person')
    calls = []
    row = {'id': deal_id, 'account_id': account, 'name': 'Example deal', 'company': 'Example',
           'stage': 'Proposal', 'owner_name': 'Alex', 'deal_value': Decimal('10000'),
           'contact_email': 'test@example.com', 'contact_phone': None,
           'last_contact_date': date(2020, 1, 1), 'stage_changed_date': date(2020, 1, 1)}

    async def db():
        yield object()

    async def listing(conn, who, requested_org):
        calls.append((who, requested_org))
        if requested_org != org:
            raise AccessDenied()
        return [row]

    async def creating(conn, who, requested_org, data):
        if requested_org != org:
            raise AccessDenied()
        return {'id': deal_id, 'company': 'Example', **data.model_dump()}

    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    monkeypatch.setattr(workspace, 'list_deals', listing)
    monkeypatch.setattr(workspace, 'create_deal', creating)
    app.dependency_overrides[workspace.workspace_identity] = lambda: identity
    app.dependency_overrides[workspace.workspace_connection] = db
    body = {'account_id': str(account), 'name': ' Deal ', 'stage': 'Proposal', 'owner_name': 'Alex',
            'deal_value': '123.45', 'last_contact_date': '2020-01-01', 'stage_changed_date': '2020-01-01'}
    try:
        with TestClient(app) as client:
            base = f'/workspace/organizations/{org}'
            assert client.post(base + '/deals', json=body).json()['name'] == 'Deal'
            assert client.post(base + '/deals', json={**body, 'name': '   '}).status_code == 422
            assert client.post(base + '/deals', json={**body, 'deal_value': '-1'}).status_code == 422
            assert client.post(base + '/deals', json={**body, 'last_contact_date': 'not-a-date'}).status_code == 422
            assert client.get(base + '/deals').status_code == 200
            scan = client.post(base + '/crm/scan')
            assert scan.status_code == 200, scan.text
            assert scan.json()['total_deals_count'] == 1
            assert scan.json()['total_alerts_count'] == 3
            assert client.get(f'/workspace/organizations/{other}/deals').status_code == 403
            assert client.post(f'/workspace/organizations/{other}/crm/scan').status_code == 403
            assert all(who == identity for who, _ in calls)
    finally:
        app.dependency_overrides.clear()


def test_empty_workspace_scan_and_missing_auth(monkeypatch):
    async def db():
        yield object()
    async def empty(*args):
        return []
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    monkeypatch.setattr(workspace, 'list_deals', empty)
    app.dependency_overrides[workspace.workspace_connection] = db
    try:
        with TestClient(app) as client:
            path = f'/workspace/organizations/{uuid4()}/crm/scan'
            assert client.post(path).status_code == 401
            app.dependency_overrides[workspace.workspace_identity] = lambda: VerifiedIdentity('https://identity.example', 'person')
            assert client.post(path).status_code == 409
    finally:
        app.dependency_overrides.clear()
