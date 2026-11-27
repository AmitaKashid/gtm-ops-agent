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


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not set')
def test_local_bootstrap_is_idempotent_and_organization_discovery_is_scoped():
    from workspace_db.bootstrap_local import bootstrap
    from workspace_db.organizations import list_organizations
    from workspace_security.identity import VerifiedIdentity

    async def run():
        conn = await asyncpg.connect(os.environ['TEST_DATABASE_URL'])
        schema = 'workspace_test_' + uuid4().hex
        try:
            await conn.execute(f'CREATE SCHEMA "{schema}"')
            await conn.execute("SELECT set_config('search_path', $1, false)", schema)
            await apply_migrations(conn, load_migrations())
            first, second = uuid4(), uuid4()
            await bootstrap(conn, first, 'First', 'issuer', 'first-user')
            await bootstrap(conn, first, 'First', 'issuer', 'first-user')
            await bootstrap(conn, second, 'Second', 'issuer', 'second-user')
            results = await list_organizations(conn, VerifiedIdentity('issuer', 'first-user'))
            assert len(results) == 1 and results[0]['id'] == first and results[0]['role'] == 'owner'
            assert await conn.fetchval('SELECT count(*) FROM workspace_audit_events') == 2
            with pytest.raises(RuntimeError, match='already has members'):
                await bootstrap(conn, first, 'First', 'issuer', 'intruder')
            assert await conn.fetchval('SELECT count(*) FROM workspace_users') == 2
        finally:
            try:
                await conn.execute('SET search_path TO public')
                await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            finally:
                await conn.close()
    asyncio.run(run())


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not set')
def test_row_security_with_non_bypass_role():
    async def run():
        conn = await asyncpg.connect(os.environ['TEST_DATABASE_URL'])
        suffix = uuid4().hex
        schema, role = 'workspace_test_' + suffix, 'workspace_role_' + suffix
        created_role = False
        try:
            await conn.execute(f'CREATE SCHEMA "{schema}"')
            await conn.execute("SELECT set_config('search_path', $1, false)", schema)
            await apply_migrations(conn, load_migrations())
            first, second = uuid4(), uuid4()
            await conn.execute('INSERT INTO workspace_organizations (id, name) VALUES ($1, $2), ($3, $4)', first, 'First', second, 'Second')
            await conn.execute('INSERT INTO workspace_accounts (organization_id, id, name) VALUES ($1, $2, $3), ($4, $5, $6)', first, uuid4(), 'First account', second, uuid4(), 'Second account')
            await conn.execute(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOBYPASSRLS')
            created_role = True
            await conn.execute(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"')
            await conn.execute(f'GRANT SELECT, INSERT ON workspace_accounts TO "{role}"')
            await conn.execute(f'SET ROLE "{role}"')
            assert await conn.fetchval('SELECT count(*) FROM workspace_accounts') == 0
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.organization_id', $1, true)", str(first))
                assert await conn.fetchval('SELECT count(*) FROM workspace_accounts') == 1
                assert await conn.fetchval('SELECT name FROM workspace_accounts') == 'First account'
            assert await conn.fetchval('SELECT count(*) FROM workspace_accounts') == 0
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                async with conn.transaction():
                    await conn.execute("SELECT set_config('app.organization_id', $1, true)", str(first))
                    await conn.execute('INSERT INTO workspace_accounts (organization_id, id, name) VALUES ($1, $2, $3)', second, uuid4(), 'Wrong tenant')
        finally:
            try:
                await conn.execute('RESET ROLE')
                await conn.execute('SET search_path TO public')
                await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
                if created_role:
                    await conn.execute(f'DROP ROLE "{role}"')
            finally:
                await conn.close()
    asyncio.run(run())


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not set')
def test_runtime_login_grants_prevent_membership_escalation():
    """Creates and removes only a random disposable database and role."""
    from workspace_db.accounts import create_account, list_accounts
    from workspace_db.runtime_grants import grant_runtime
    from workspace_security.authorization import AccessDenied
    from workspace_security.database_guard import UnsafeDatabaseRole, require_safe_database_role
    from workspace_security.identity import VerifiedIdentity

    async def run():
        admin = await asyncpg.connect(os.environ['TEST_DATABASE_URL'])
        suffix = uuid4().hex
        database, role, password = 'ws_test_' + suffix, 'ws_user_' + suffix, uuid4().hex
        db_created = role_created = False
        owner = runtime = None
        try:
            await admin.execute(f'CREATE DATABASE "{database}"')
            db_created = True
            await admin.execute(f'CREATE ROLE "{role}" LOGIN PASSWORD \'{password}\' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
            role_created = True
            owner = await asyncpg.connect(os.environ['TEST_DATABASE_URL'], database=database)
            await apply_migrations(owner, load_migrations())
            org, other, user = uuid4(), uuid4(), uuid4()
            await owner.execute('INSERT INTO workspace_organizations (id, name) VALUES ($1, $2), ($3, $4)', org, 'First', other, 'Second')
            await owner.execute('INSERT INTO workspace_users (id, identity_issuer, identity_subject) VALUES ($1, $2, $3)', user, 'issuer', 'subject')
            await owner.execute("INSERT INTO workspace_memberships (organization_id, user_id, role) VALUES ($1, $2, 'member')", org, user)
            await grant_runtime(owner, role)
            runtime = await asyncpg.connect(os.environ['TEST_DATABASE_URL'], database=database, user=role, password=password)
            await require_safe_database_role(runtime)
            identity = VerifiedIdentity('issuer', 'subject')
            assert (await create_account(runtime, identity, org, 'Example'))['name'] == 'Example'
            assert len(await list_accounts(runtime, identity, org)) == 1
            with pytest.raises(AccessDenied):
                await list_accounts(runtime, identity, other)
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await runtime.execute("UPDATE workspace_memberships SET role = 'owner' WHERE user_id = $1", user)
            await owner.execute(f'GRANT UPDATE (role) ON workspace_memberships TO "{role}"')
            with pytest.raises(UnsafeDatabaseRole):
                await require_safe_database_role(runtime)
        finally:
            if runtime is not None:
                await runtime.close()
            if owner is not None:
                await owner.close()
            try:
                if db_created:
                    await admin.execute(f'DROP DATABASE "{database}"')
                if role_created:
                    await admin.execute(f'DROP ROLE "{role}"')
            finally:
                await admin.close()
    asyncio.run(run())
