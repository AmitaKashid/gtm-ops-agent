"""Provision the first workspace owner using an administrator connection.

Run manually, never from a web endpoint. Do not use the runtime login.
"""
import argparse
import asyncio
import os
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from workspace_db.bootstrap_local import bootstrap


def validate_hosted_config(database_url, issuer):
    db = urlsplit(database_url)
    modes = parse_qs(db.query).get('sslmode', [])
    if db.scheme not in {'postgres', 'postgresql'} or not db.hostname or modes != ['verify-full']:
        raise ValueError('Admin database URL must specify sslmode=verify-full')
    if db.hostname in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('Use bootstrap_local for loopback development')
    provider = urlsplit(issuer)
    if provider.scheme != 'https' or not provider.hostname or provider.username or provider.password or provider.fragment or provider.query:
        raise ValueError('Identity issuer must be an HTTPS issuer URL')


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--organization-id', type=UUID, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--issuer', required=True)
    parser.add_argument('--subject', required=True)
    args = parser.parse_args()
    url = os.environ.get('WORKSPACE_ADMIN_DATABASE_URL', '')
    validate_hosted_config(url, args.issuer)
    import asyncpg
    connection = await asyncpg.connect(url, timeout=10)
    try:
        await bootstrap(connection, args.organization_id, args.name, args.issuer, args.subject)
    finally:
        await connection.close()
    print('Initial workspace owner is configured.')


if __name__ == '__main__':
    asyncio.run(main())
