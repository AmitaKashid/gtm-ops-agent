from fastapi.testclient import TestClient
from api.main import app


def test_workspace_ui_is_disabled_in_public_demo(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.setenv('PUBLIC_DEMO', 'true')
    client = TestClient(app)
    assert client.get('/workspace-app').status_code == 404
    assert client.get('/workspace-app.js').status_code == 404


def test_workspace_ui_is_available_when_enabled_locally(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    client = TestClient(app)
    assert client.get('/workspace-app').status_code == 200
    assert client.get('/workspace-app.js').status_code == 200


def test_hosted_workspace_ui_is_opt_in_and_disabled_for_public_demo(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.delenv('WORKSPACE_HOSTED_UI_ENABLED', raising=False)
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    client = TestClient(app)
    assert client.get('/workspace-app').status_code == 404
    monkeypatch.setenv('WORKSPACE_HOSTED_UI_ENABLED', 'true')
    assert client.get('/workspace-app').status_code == 200
    assert client.get('/workspace-config').status_code == 503
    monkeypatch.setenv('PUBLIC_DEMO', 'true')
    assert client.get('/workspace-app').status_code == 404
    assert client.get('/workspace-config').status_code == 404


def test_browser_config_returns_only_validated_public_fields(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.setenv('WORKSPACE_HOSTED_UI_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    monkeypatch.setenv('WORKSPACE_OIDC_ISSUER', 'https://identity.example/realms/gtm')
    monkeypatch.setenv('WORKSPACE_OIDC_JWKS_URL', 'https://identity.example/realms/gtm/jwks')
    monkeypatch.setenv('WORKSPACE_OIDC_AUDIENCE', 'workspace-api')
    monkeypatch.setenv('WORKSPACE_OIDC_CLIENT_ID', 'workspace-web')
    monkeypatch.setenv('WORKSPACE_DATABASE_URL', 'postgresql://secret-credentials')
    client = TestClient(app)
    result = client.get('/workspace-config')
    assert result.status_code == 200
    assert result.json() == {'issuer': 'https://identity.example/realms/gtm', 'client_id': 'workspace-web'}
    assert result.headers['cache-control'] == 'no-store'
    monkeypatch.setenv('WORKSPACE_OIDC_ISSUER', 'http://identity.example/realms/gtm')
    assert client.get('/workspace-config').status_code == 503


def test_hosted_workspace_disables_legacy_unauthenticated_workflows(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('WORKSPACE_ENABLED', 'true')
    monkeypatch.setenv('WORKSPACE_HOSTED_UI_ENABLED', 'true')
    monkeypatch.delenv('PUBLIC_DEMO', raising=False)
    client = TestClient(app)
    assert client.post('/leads/analyze', json={}).status_code == 404
    assert client.post('/crm/scan', json={}).status_code == 404
    assert client.get('/health').status_code == 200
    assert client.get('/', follow_redirects=False).headers['location'] == '/workspace-app'
    assert client.get('/workspace/organizations').status_code == 401
