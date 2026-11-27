import asyncio

import pytest

from workspace_db.runtime_grants import grant_runtime


def test_invalid_runtime_role_rejected_before_database_access():
    class NoConnection:
        def __getattr__(self, key):
            raise AssertionError('Database should not be accessed')

    for role in ('some-role', 'postgres;DROP TABLE x', 'UPPERCASE', '', 'a' * 64):
        with pytest.raises(ValueError):
            asyncio.run(grant_runtime(NoConnection(), role))
