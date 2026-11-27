import json
from pathlib import Path


def test_local_keycloak_client_uses_pkce_and_access_token_audience():
    root = Path(__file__).resolve().parents[1]
    realm = json.loads((root / 'keycloak/realm-gtm-dev.json').read_text())
    assert realm['registrationAllowed'] is False
    client, = realm['clients']
    assert client['publicClient'] is True
    assert client['directAccessGrantsEnabled'] is False
    assert client['attributes']['pkce.code.challenge.method'] == 'S256'
    mapper, = client['protocolMappers']
    assert mapper['config']['included.custom.audience'] == 'gtm-workspace-api'
    assert mapper['config']['access.token.claim'] == 'true'
    assert mapper['config']['id.token.claim'] == 'false'
