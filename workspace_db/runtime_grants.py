"""Grant the minimum privileges used by the workspace API to an existing role.

Run with a database owner connection and a separately created, dedicated login.
This adds grants; it does not create logins, set passwords, or revoke existing
privileges. Use the guard to reject privileges inherited from other roles.
"""
import argparse
import asyncio
import os
import re


async def grant_runtime(connection, role):
    if not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', role):
        raise ValueError('Role name must use lowercase ASCII letters, digits and underscores')
    # Identifiers are whitelisted above, not interpolated from user input as SQL.
    quoted = '"' + role + '"'
    schema = await connection.fetchval('SELECT current_schema()')
    if schema != 'public':
        raise RuntimeError('The runtime grant command requires the public schema')
    exists = await connection.fetchval('SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname=$1)', role)
    if not exists:
        raise RuntimeError('Create the dedicated database login separately before granting access')
    async with connection.transaction():
        await connection.execute(f'GRANT USAGE ON SCHEMA public TO {quoted}')
        await connection.execute(f'GRANT SELECT ON workspace_organizations, workspace_users, workspace_memberships TO {quoted}')
        # PostgreSQL requires an UPDATE privilege for SELECT ... FOR SHARE.
        # This column does not control an identity, organization, or role.
        await connection.execute(f'GRANT UPDATE (created_at) ON workspace_memberships TO {quoted}')
        await connection.execute(f'GRANT SELECT, INSERT ON workspace_accounts TO {quoted}')
        await connection.execute(f'GRANT INSERT ON workspace_audit_events TO {quoted}')


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', required=True, help='Existing dedicated runtime login (not the owner)')
    args = parser.parse_args()
    url = os.environ.get('WORKSPACE_ADMIN_DATABASE_URL')
    if not url:
        raise RuntimeError('Set WORKSPACE_ADMIN_DATABASE_URL to an owner connection privately')
    import asyncpg
    connection = await asyncpg.connect(url, timeout=10)
    try:
        await grant_runtime(connection, args.role)
    finally:
        await connection.close()
    print('Runtime grants applied. Check the API role guard before enabling the workspace.')


if __name__ == '__main__':
    asyncio.run(main())
