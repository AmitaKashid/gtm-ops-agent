import os
import time
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import workspace
from workspace_security import identity as identity_module


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(workspace.router)
    return app


@pytest.fixture
def token_setup(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    monkeypatch.setenv('WORKSPACE_OIDC_ISSUER', 'https://id.example/')
    monkeypatch.setenv('WORKSPACE_OIDC_AUDIENCE', 'workspace-api')
    monkeypatch.setenv('WORKSPACE_OIDC_JWKS_URL', 'https://id.example/jwks')
    client = SimpleNamespace(get_signing_key_from_jwt=lambda value: SimpleNamespace(key=key.public_key()))
    monkeypatch.setattr(identity_module, '_jwks_client', lambda url: client)
    def make_token(**kwargs):
        now = int(time.time())
        claims = {'iss': 'https://id.example/', 'aud': 'workspace-api', 'sub': 'person', 'iat': now, 'exp': now + 60}
        claims.update(kwargs)
        return jwt.encode(claims, key, algorithm='RS256')
    return make_token


def test_disabled_workspace_fails_closed(app, monkeypatch):
    monkeypatch.delenv('WORKSPACE_ENABLED', raising=False)
    assert TestClient(app).get(f'/workspace/organizations/{uuid4()}/accounts').status_code == 503


def test_public_demo_disables_workspace_even_if_enabled(app, token_setup, monkeypatch):
    monkeypatch.setenv('PUBLIC_DEMO', 'true')
    response = TestClient(app).get(f'/workspace/organizations/{uuid4()}/accounts', headers={'Authorization': 'Bearer ' + token_setup()})
    assert response.status_code == 503


def test_missing_or_invalid_token_rejected(app, token_setup):
    client = TestClient(app)
    path = f'/workspace/organizations/{uuid4()}/accounts'
    assert client.get(path).status_code == 401
    assert client.get(path, headers={'Authorization': 'Bearer ' + token_setup(aud='wrong')}).status_code == 401


def test_authenticated_member_can_list_and_denial_is_403(app, token_setup, monkeypatch):
    async def fake_db():
        yield object()
    app.dependency_overrides[workspace.workspace_connection] = fake_db
    seen = []
    async def fake_list(conn, identity, org):
        seen.append((identity.subject, org))
        return []
    monkeypatch.setattr(workspace, 'list_accounts', fake_list)
    org = uuid4()
    client = TestClient(app)
    headers = {'Authorization': 'Bearer ' + token_setup()}
    response = client.get(f'/workspace/organizations/{org}/accounts', headers=headers)
    assert response.status_code == 200
    assert seen == [('person', org)]
    async def deny(*args):
        raise workspace.AccessDenied()
    monkeypatch.setattr(workspace, 'list_accounts', deny)
    assert client.get(f'/workspace/organizations/{org}/accounts', headers=headers).status_code == 403


def test_organization_discovery_requires_verified_identity(app, token_setup, monkeypatch):
    async def fake_db():
        yield object()
    app.dependency_overrides[workspace.workspace_connection] = fake_db
    seen = []
    async def fake_list(conn, identity):
        seen.append(identity.subject)
        return []
    monkeypatch.setattr(workspace, 'list_organizations', fake_list)
    client = TestClient(app)
    assert client.get('/workspace/organizations').status_code == 401
    response = client.get('/workspace/organizations', headers={'Authorization': 'Bearer ' + token_setup()})
    assert response.status_code == 200
    assert seen == ['person']


def test_insecure_loopback_requires_development_and_explicit_opt_in(app, token_setup, monkeypatch):
    issuer = 'http://127.0.0.1:8088/realms/gtm'
    monkeypatch.setenv('WORKSPACE_OIDC_ISSUER', issuer)
    monkeypatch.setenv('WORKSPACE_OIDC_JWKS_URL', issuer + '/protocol/openid-connect/certs')
    monkeypatch.setenv('WORKSPACE_ALLOW_INSECURE_LOCAL_OIDC', 'true')
    headers = {'Authorization': 'Bearer ' + token_setup(iss=issuer)}
    path = f'/workspace/organizations/{uuid4()}/accounts'
    async def fake_db():
        yield object()
    async def fake_list(*args):
        return []
    app.dependency_overrides[workspace.workspace_connection] = fake_db
    monkeypatch.setattr(workspace, 'list_accounts', fake_list)
    client = TestClient(app)
    monkeypatch.setenv('APP_ENV', 'production')
    assert client.get(path, headers=headers).status_code == 503
    monkeypatch.setenv('APP_ENV', 'development')
    assert client.get(path, headers=headers).status_code == 200
    monkeypatch.delenv('WORKSPACE_ALLOW_INSECURE_LOCAL_OIDC')
    assert client.get(path, headers=headers).status_code == 503


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not set')
def test_signed_access_token_membership_and_audit_against_postgres(token_setup):
    import asyncio
    import asyncpg
    import httpx
    from workspace_db.migrate import apply_migrations, load_migrations

    async def run():
        conn = await asyncpg.connect(os.environ['TEST_DATABASE_URL'])
        schema = 'workspace_test_' + uuid4().hex
        try:
            await conn.execute(f'CREATE SCHEMA "{schema}"')
            await conn.execute("SELECT set_config('search_path', $1, false)", schema)
            await apply_migrations(conn, load_migrations())
            first, second, user = uuid4(), uuid4(), uuid4()
            await conn.execute('INSERT INTO workspace_organizations(id, name) VALUES ($1, $2), ($3, $4)', first, 'First', second, 'Second')
            await conn.execute('INSERT INTO workspace_users(id, identity_issuer, identity_subject) VALUES ($1, $2, $3)', user, 'https://id.example/', 'person')
            await conn.execute('INSERT INTO workspace_memberships(organization_id, user_id, role) VALUES ($1, $2, $3)', first, user, 'member')
            app = FastAPI()
            app.include_router(workspace.router)
            async def db():
                yield conn
            app.dependency_overrides[workspace.workspace_connection] = db
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                headers = {'Authorization': 'Bearer ' + token_setup()}
                path = f'/workspace/organizations/{first}/accounts'
                assert (await client.get(path)).status_code == 401
                response = await client.post(path, headers=headers, json={'name': 'Acme'})
                assert response.status_code == 201, response.text
                assert response.json()['name'] == 'Acme'
                assert len((await client.get(path, headers=headers)).json()) == 1
                assert (await client.get(f'/workspace/organizations/{second}/accounts', headers=headers)).status_code == 403
                assert (await client.post(f'/workspace/organizations/{second}/accounts', headers=headers, json={'name': 'Forbidden'})).status_code == 403
                await conn.execute("UPDATE workspace_memberships SET role = 'viewer' WHERE user_id = $1", user)
                assert (await client.post(path, headers=headers, json={'name': 'Forbidden'})).status_code == 403
            assert await conn.fetchval('SELECT count(*) FROM workspace_accounts') == 1
            assert await conn.fetchval('SELECT count(*) FROM workspace_audit_events WHERE actor_id = $1', user) == 1
        finally:
            try:
                await conn.execute('SET search_path TO public')
                await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            finally:
                await conn.close()
    asyncio.run(run())
