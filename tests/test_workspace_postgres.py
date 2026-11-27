"""PostgreSQL integration tests. Set TEST_DATABASE_URL to an isolated test DB."""
import asyncio
import os
from uuid import uuid4

import asyncpg
import pytest

from workspace_db.migrate import apply_migrations, load_migrations


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not set')
def test_migrations_and_tenant_relations_on_postgres():
    async def run():
        conn = await asyncpg.connect(os.environ['TEST_DATABASE_URL'])
        schema = 'workspace_test_' + uuid4().hex
        try:
            await conn.execute(f'CREATE SCHEMA "{schema}"')
            await conn.execute("SELECT set_config('search_path', $1, false)", schema)
            migrations = load_migrations()
            await apply_migrations(conn, migrations)
            await apply_migrations(conn, migrations)
            count = await conn.fetchval('SELECT count(*) FROM workspace_schema_migrations')
            assert count == len(migrations)
            first, second, account, contact = (uuid4() for _ in range(4))
            await conn.execute('INSERT INTO workspace_organizations(id, name) VALUES ($1, $2), ($3, $4)', first, 'First', second, 'Second')
            await conn.execute('INSERT INTO workspace_accounts(organization_id, id, name) VALUES ($1, $2, $3)', first, account, 'Example')
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                await conn.execute('INSERT INTO workspace_contacts(organization_id, id, account_id, name) VALUES ($1, $2, $3, $4)', second, contact, account, 'Contact')
            assert await conn.fetchval('SELECT count(*) FROM workspace_contacts') == 0
            await conn.execute('INSERT INTO workspace_contacts(organization_id, id, account_id, name) VALUES ($1, $2, $3, $4)', first, contact, account, 'Contact')
            assert await conn.fetchval('SELECT count(*) FROM workspace_contacts') == 1
            from workspace_security.authorization import AccessDenied, Permission, require_membership
            from workspace_security.identity import VerifiedIdentity

            user = uuid4()
            await conn.execute('INSERT INTO workspace_users(id, identity_issuer, identity_subject) VALUES ($1, $2, $3)', user, 'https://id.example/', 'user-1')
            await conn.execute('INSERT INTO workspace_memberships(organization_id, user_id, role) VALUES ($1, $2, $3)', first, user, 'viewer')
            identity = VerifiedIdentity('https://id.example/', 'user-1')
            async with conn.transaction():
                assert await require_membership(conn, identity, first, Permission.READ) == 'viewer'
                with pytest.raises(AccessDenied):
                    await require_membership(conn, identity, first, Permission.WRITE)
                with pytest.raises(AccessDenied):
                    await require_membership(conn, identity, second, Permission.READ)
        finally:
            try:
                await conn.execute('SET search_path TO public')
                await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            finally:
                await conn.close()
    asyncio.run(run())


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not set')
def test_failing_migration_rolls_back_all_changes():
    async def run():
        conn = await asyncpg.connect(os.environ['TEST_DATABASE_URL'])
        schema = 'workspace_test_' + uuid4().hex
        try:
            await conn.execute(f'CREATE SCHEMA "{schema}"')
            await conn.execute("SELECT set_config('search_path', $1, false)", schema)
            with pytest.raises(asyncpg.PostgresError):
                await apply_migrations(conn, [('001_good.sql', b'CREATE TABLE first_table (id int);'), ('002_bad.sql', b'INVALID SQL;')])
            assert await conn.fetchval("SELECT to_regclass('first_table')") is None
            assert await conn.fetchval("SELECT to_regclass('workspace_schema_migrations')") is None
        finally:
            try:
                await conn.execute('SET search_path TO public')
                await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            finally:
                await conn.close()
    asyncio.run(run())


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not set')
def test_accounts_are_scoped_and_writes_are_audited():
    from workspace_db.accounts import create_account, list_accounts
    from workspace_security.authorization import AccessDenied
    from workspace_security.identity import VerifiedIdentity

    async def run():
        conn = await asyncpg.connect(os.environ['TEST_DATABASE_URL'])
        schema = 'workspace_test_' + uuid4().hex
        try:
            await conn.execute(f'CREATE SCHEMA "{schema}"')
            await conn.execute("SELECT set_config('search_path', $1, false)", schema)
            await apply_migrations(conn, load_migrations())
            first, second, user = uuid4(), uuid4(), uuid4()
            await conn.execute('INSERT INTO workspace_organizations(id, name) VALUES ($1, $2), ($3, $4)', first, 'First', second, 'Second')
            await conn.execute('INSERT INTO workspace_users(id, identity_issuer, identity_subject) VALUES ($1, $2, $3)', user, 'https://id.example/', 'user-1')
            await conn.execute('INSERT INTO workspace_memberships(organization_id, user_id, role) VALUES ($1, $2, $3)', first, user, 'member')
            identity = VerifiedIdentity('https://id.example/', 'user-1')
            created = await create_account(conn, identity, first, '  Acme  ')
            assert created['name'] == 'Acme'
            assert len(await list_accounts(conn, identity, first)) == 1
            with pytest.raises(AccessDenied):
                await list_accounts(conn, identity, second)
            with pytest.raises(AccessDenied):
                await create_account(conn, identity, second, 'Forbidden')
            assert await conn.fetchval('SELECT count(*) FROM workspace_accounts') == 1
            assert await conn.fetchval('SELECT count(*) FROM workspace_audit_events WHERE organization_id = $1 AND actor_id = $2', first, user) == 1
            await conn.execute("UPDATE workspace_memberships SET role = 'viewer' WHERE user_id = $1", user)
            with pytest.raises(AccessDenied):
                await create_account(conn, identity, first, 'Forbidden')
            assert await conn.fetchval('SELECT count(*) FROM workspace_accounts') == 1
        finally:
            try:
                await conn.execute('SET search_path TO public')
                await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            finally:
                await conn.close()
    asyncio.run(run())
