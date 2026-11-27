import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from workspace_security.identity import IdentitySettings, InvalidAccessToken, verify_access_token


@pytest.fixture(scope='module')
def keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private_key.public_key()))


def settings():
    return IdentitySettings('https://identity.example/', 'https://api.example/', 'https://identity.example/jwks')


def token(private_key, **changes):
    now = int(time.time())
    claims = {'iss': 'https://identity.example/', 'aud': 'https://api.example/', 'sub': 'user-1', 'iat': now, 'exp': now + 60}
    claims.update(changes)
    return jwt.encode(claims, private_key, algorithm='RS256', headers={'kid': 'test-key'})


def test_verified_identity(keys):
    private_key, client = keys
    identity = verify_access_token(token(private_key), settings(), key_client=client)
    assert (identity.issuer, identity.subject) == ('https://identity.example/', 'user-1')


@pytest.mark.parametrize('changes', [
    {'iss': 'https://wrong.example/'},
    {'aud': 'https://wrong.example/'},
    {'exp': 1},
    {'sub': ''},
])
def test_invalid_claims_are_rejected(keys, changes):
    private_key, client = keys
    with pytest.raises(InvalidAccessToken):
        verify_access_token(token(private_key, **changes), settings(), key_client=client)


def test_wrong_signing_key_is_rejected(keys):
    _, client = keys
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(InvalidAccessToken):
        verify_access_token(token(wrong_key), settings(), key_client=client)


def test_identity_provider_settings_require_https():
    with pytest.raises(ValueError):
        IdentitySettings('http://identity.example/', 'aud', 'https://identity.example/jwks')
