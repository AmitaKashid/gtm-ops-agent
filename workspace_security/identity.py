"""Verify access tokens from an explicitly configured OIDC identity provider.

This module does not install routes or authorize access to any resource.
"""
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

import jwt


class InvalidAccessToken(Exception):
    """Token verification failed. Do not log the token or decoded claims."""


@dataclass(frozen=True)
class IdentitySettings:
    issuer: str
    audience: str
    jwks_url: str
    allow_insecure_loopback: bool = False

    def __post_init__(self):
        if not self.issuer or not self.audience or not self.jwks_url:
            raise ValueError('Issuer, audience and JWKS URL are required')
        for value in (self.issuer, self.jwks_url):
            parsed = urlsplit(value)
            local_http = self.allow_insecure_loopback and parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1', '::1'}
            if (parsed.scheme != 'https' and not local_http) or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError('Issuer and JWKS URL must use HTTPS, except explicit loopback development')


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str


@lru_cache(maxsize=8)
def _jwks_client(jwks_url):
    return jwt.PyJWKClient(jwks_url, cache_keys=False, cache_jwk_set=True, lifespan=300, timeout=5)


def verify_access_token(token, settings, *, key_client=None):
    """Verify RS256 signature, issuer, audience, expiry and required claims.

    Configure an API-specific audience; do not accept an ID token as an API
    access token. The identity provider must issue an RS256 JWT access token.
    """
    if not isinstance(token, str) or not token or len(token) > 8192:
        raise InvalidAccessToken('Invalid access token')
    try:
        client = key_client if key_client is not None else _jwks_client(settings.jwks_url)
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key, algorithms=['RS256'],
            audience=settings.audience, issuer=settings.issuer,
            options={'require': ['exp', 'iat', 'iss', 'sub', 'aud']},
        )
        if not isinstance(claims['sub'], str) or not claims['sub'].strip():
            raise InvalidAccessToken('Invalid access token')
        return VerifiedIdentity(issuer=claims['iss'], subject=claims['sub'])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
        raise InvalidAccessToken('Invalid access token') from exc
