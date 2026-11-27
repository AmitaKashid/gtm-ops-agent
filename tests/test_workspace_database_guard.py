import asyncio

import pytest

from workspace_security.database_guard import PROTECTED_TABLES, UnsafeDatabaseRole, require_safe_database_role


class Connection:
    def __init__(self, role=None, rows=None):
        self.role = role if role is not None else {'direct_login': True, 'can_bypass': False}
        self.rows = rows if rows is not None else [
            {'relname': name, 'relrowsecurity': True, 'relforcerowsecurity': True, 'can_own': False}
            for name in PROTECTED_TABLES
        ]

    async def fetchrow(self, sql):
        return self.role

    async def fetch(self, sql, names):
        return self.rows


def test_safe_role_and_policies_accepted():
    asyncio.run(require_safe_database_role(Connection()))


@pytest.mark.parametrize('role', [
    {'direct_login': False, 'can_bypass': False},
    {'direct_login': True, 'can_bypass': True},
])
def test_role_that_can_bypass_is_rejected(role):
    with pytest.raises(UnsafeDatabaseRole):
        asyncio.run(require_safe_database_role(Connection(role=role)))


@pytest.mark.parametrize('field', ['relrowsecurity', 'relforcerowsecurity', 'can_own'])
def test_missing_policy_or_owner_role_is_rejected(field):
    conn = Connection()
    conn.rows[0][field] = field == 'can_own'
    with pytest.raises(UnsafeDatabaseRole):
        asyncio.run(require_safe_database_role(conn))


def test_missing_table_is_rejected():
    with pytest.raises(UnsafeDatabaseRole):
        asyncio.run(require_safe_database_role(Connection(rows=[])))
