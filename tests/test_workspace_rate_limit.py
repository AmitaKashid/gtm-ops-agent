import asyncio
from types import SimpleNamespace

import pytest

from workspace_security.rate_limit import RateLimitConfigurationError, configured_limit, consume_workspace_request


class Connection:
    def __init__(self, result):
        self.result = result
        self.values = None
    async def fetchval(self, sql, *args):
        self.values = args
        return self.result


def test_rate_limiter_hashes_identity_and_checks_atomic_result():
    identity = SimpleNamespace(issuer='https://id.example', subject='private-subject')
    conn = Connection(1)
    assert asyncio.run(consume_workspace_request(conn, identity, 3))
    assert len(conn.values[0]) == 64 and 'private-subject' not in conn.values[0]
    assert conn.values[1] == 3
    assert not asyncio.run(consume_workspace_request(Connection(None), identity, 3))


@pytest.mark.parametrize('value', ['zero', '0', '-1', '10001'])
def test_rate_limit_misconfiguration_fails_closed(monkeypatch, value):
    monkeypatch.setenv('WORKSPACE_RATE_LIMIT_PER_MINUTE', value)
    with pytest.raises(RateLimitConfigurationError):
        configured_limit()
