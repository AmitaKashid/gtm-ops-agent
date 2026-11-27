import asyncio
import hashlib

import pytest

from workspace_db.migrate import apply_migrations, load_migrations


class Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class Connection:
    def __init__(self, rows=()):
        self.rows = rows
        self.calls = []

    def transaction(self):
        return Transaction()

    async def execute(self, sql, *args):
        self.calls.append((sql, args))

    async def fetch(self, sql):
        return self.rows


def test_new_migration_executes_and_is_recorded():
    conn = Connection()
    asyncio.run(apply_migrations(conn, [('001_test.sql', b'SELECT 1;')]))
    assert any(sql == 'SELECT 1;' for sql, _ in conn.calls)
    assert any('INSERT INTO workspace_schema_migrations' in sql for sql, _ in conn.calls)


def test_existing_migration_is_not_reapplied():
    checksum = hashlib.sha256(b'SELECT 1;').hexdigest()
    conn = Connection([{'filename': '001_test.sql', 'checksum': checksum}])
    asyncio.run(apply_migrations(conn, [('001_test.sql', b'SELECT 1;')]))
    assert not any(sql == 'SELECT 1;' for sql, _ in conn.calls)


def test_changed_migration_is_rejected():
    conn = Connection([{'filename': '001_test.sql', 'checksum': 'wrong'}])
    with pytest.raises(RuntimeError, match='Checksum mismatch'):
        asyncio.run(apply_migrations(conn, [('001_test.sql', b'SELECT 1;')]))


def test_unknown_database_migration_is_rejected():
    conn = Connection([{'filename': '999_unknown.sql', 'checksum': 'x'}])
    with pytest.raises(RuntimeError, match='unknown'):
        asyncio.run(apply_migrations(conn, [('001_test.sql', b'SELECT 1;')]))


def test_migration_version_must_be_unique(tmp_path):
    (tmp_path / '001_a.sql').write_text('SELECT 1;')
    (tmp_path / '001_b.sql').write_text('SELECT 2;')
    with pytest.raises(RuntimeError, match='Duplicate'):
        load_migrations(tmp_path)
