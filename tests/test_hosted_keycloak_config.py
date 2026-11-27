import json
from pathlib import Path


def test_hosted_realm_requires_pkce_and_limits_redirects():
    realm = json.loads(Path('keycloak/hosted/gtm-realm.json').read_text(encoding='utf-8'))
    assert realm['sslRequired'] == 'all'
    assert realm['registrationAllowed'] is False
    client = realm['clients'][0]
    assert client['publicClient'] is True
    assert client['implicitFlowEnabled'] is False
    assert client['directAccessGrantsEnabled'] is False
    assert client['attributes']['pkce.code.challenge.method'] == 'S256'
    assert client['redirectUris'] == ['${WORKSPACE_ORIGIN}/workspace-app']
    assert client['webOrigins'] == ['${WORKSPACE_ORIGIN}']
    config = client['protocolMappers'][0]['config']
    assert config['included.custom.audience'] == 'gtm-workspace-api'
    assert config['access.token.claim'] == 'true'
    assert config['id.token.claim'] == 'false'
