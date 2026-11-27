import asyncio
from uuid import uuid4

import pytest

from workspace_security.authorization import AccessDenied, Permission, require_membership
from workspace_security.identity import VerifiedIdentity


class Connection:
    def __init__(self, role):
        self.role = role
        self.args = None

    def is_in_transaction(self):
        return True

    async def fetchval(self, query, *args):
        self.args = args
        return self.role


@pytest.mark.parametrize(('role', 'permission', 'allowed'), [
    ('owner', Permission.MANAGE_MEMBERS, True),
    ('admin', Permission.MANAGE_MEMBERS, True),
    ('member', Permission.MANAGE_MEMBERS, False),
    ('member', Permission.WRITE, True),
    ('viewer', Permission.WRITE, False),
    ('viewer', Permission.READ, True),
    ('unknown', Permission.READ, False),
    (None, Permission.READ, False),
])
def test_role_permissions(role, permission, allowed):
    conn, org = Connection(role), uuid4()
    identity = VerifiedIdentity('https://id.example/', 'user-1')
    if allowed:
        assert asyncio.run(require_membership(conn, identity, org, permission)) == role
    else:
        with pytest.raises(AccessDenied):
            asyncio.run(require_membership(conn, identity, org, permission))
    assert conn.args == (org, identity.issuer, identity.subject)


def test_invalid_permission_fails_closed():
    with pytest.raises(AccessDenied):
        asyncio.run(require_membership(Connection('owner'), VerifiedIdentity('issuer', 'subject'), uuid4(), 'read'))


def test_transaction_is_required():
    conn = Connection('owner')
    conn.is_in_transaction = lambda: False
    with pytest.raises(RuntimeError, match='active transaction'):
        asyncio.run(require_membership(conn, VerifiedIdentity('issuer', 'subject'), uuid4(), Permission.READ))
