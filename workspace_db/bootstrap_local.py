"""Create a local development workspace with a manually selected OIDC subject.

This command intentionally refuses remote database hosts and production mode.
It is not an invitation, registration, or production provisioning workflow.
"""
import argparse
import asyncio
import os
from urllib.parse import urlsplit
from uuid import UUID, uuid4


def validate_environment(url, environment, demo):
    if environment != 'development' or demo.lower() == 'true':
        raise RuntimeError('Bootstrap requires APP_ENV=development and PUBLIC_DEMO disabled')
    parsed = urlsplit(url)
    if parsed.scheme not in {'postgres', 'postgresql'} or parsed.hostname not in {'localhost', '127.0.0.1', '::1'} or parsed.query or parsed.fragment:
        raise RuntimeError('Bootstrap requires an explicitly configured loopback PostgreSQL URL')


async def bootstrap(connection, organization_id, name, issuer, subject):
    if not 1 <= len(name.strip()) <= 200 or not issuer or not subject:
        raise ValueError('Organization name, issuer, and subject are required')
    async with connection.transaction():
        await connection.execute('SELECT pg_advisory_xact_lock($1)', 7198452154902)
        await connection.execute('INSERT INTO workspace_organizations (id, name) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING', organization_id, name.strip())
        current_name = await connection.fetchval('SELECT name FROM workspace_organizations WHERE id = $1', organization_id)
        if current_name != name.strip():
            raise RuntimeError('Organization ID already belongs to a different name')
        await connection.execute('INSERT INTO workspace_users (id, identity_issuer, identity_subject) VALUES ($1, $2, $3) ON CONFLICT (identity_issuer, identity_subject) DO NOTHING', uuid4(), issuer, subject)
        user = await connection.fetchval('SELECT id FROM workspace_users WHERE identity_issuer = $1 AND identity_subject = $2', issuer, subject)
        # Refuse to silently elevate an existing membership.
        role = await connection.fetchval('SELECT role FROM workspace_memberships WHERE organization_id = $1 AND user_id = $2', organization_id, user)
        if role is not None and role != 'owner':
            raise RuntimeError('Existing member is not an owner; refusing role change')
        if role is None:
            # Never create another owner for an existing organization.
            existing = await connection.fetchval('SELECT EXISTS(SELECT 1 FROM workspace_memberships WHERE organization_id = $1)', organization_id)
            if existing:
                raise RuntimeError('Organization already has members; bootstrap cannot add another owner')
            await connection.execute("INSERT INTO workspace_memberships (organization_id, user_id, role) VALUES ($1, $2, 'owner')", organization_id, user)
            await connection.execute("SELECT set_config('app.organization_id', $1, true)", str(organization_id))
            await connection.execute('''INSERT INTO workspace_audit_events
                (organization_id, id, actor_id, action, object_type, object_id)
                VALUES ($1, $2, $3, 'workspace.bootstrap', 'organization', $1)''', organization_id, uuid4(), user)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--organization-id', type=UUID, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--issuer', required=True)
    parser.add_argument('--subject', required=True)
    args = parser.parse_args()
    url = os.environ.get('WORKSPACE_DATABASE_URL', '')
    validate_environment(url, os.getenv('APP_ENV', ''), os.getenv('PUBLIC_DEMO', ''))
    import asyncpg
    conn = await asyncpg.connect(url, timeout=5)
    try:
        await bootstrap(conn, args.organization_id, args.name, args.issuer, args.subject)
    finally:
        await conn.close()
    print('Local development workspace is ready.')


if __name__ == '__main__':
    asyncio.run(main())
