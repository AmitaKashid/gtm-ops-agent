"""Tenant-scoped account operations for the future authenticated workspace.

Call only with a server-verified identity. These functions do not expose API
routes and do not verify or decode tokens themselves.
"""
from uuid import UUID, uuid4

from workspace_security.authorization import Permission, require_membership
from workspace_security.identity import VerifiedIdentity


async def list_accounts(connection, identity: VerifiedIdentity, organization_id: UUID):
    async with connection.transaction():
        await require_membership(connection, identity, organization_id, Permission.READ)
        rows = await connection.fetch('''
            SELECT id, name, created_at FROM workspace_accounts
            WHERE organization_id = $1 ORDER BY created_at DESC, id DESC LIMIT 100
        ''', organization_id)
        return [dict(row) for row in rows]


async def create_account(connection, identity: VerifiedIdentity, organization_id: UUID, name: str):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 255:
        raise ValueError('Account name must contain 1 to 255 characters')
    name = name.strip()
    async with connection.transaction():
        await require_membership(connection, identity, organization_id, Permission.WRITE)
        actor = await connection.fetchval('''
            SELECT id FROM workspace_users WHERE identity_issuer = $1 AND identity_subject = $2
        ''', identity.issuer, identity.subject)
        account_id, event_id = uuid4(), uuid4()
        row = await connection.fetchrow('''
            INSERT INTO workspace_accounts (organization_id, id, name)
            VALUES ($1, $2, $3) RETURNING id, name, created_at
        ''', organization_id, account_id, name)
        await connection.execute('''
            INSERT INTO workspace_audit_events
                (organization_id, id, actor_id, action, object_type, object_id)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', organization_id, event_id, actor, 'account.created', 'account', account_id)
        return dict(row)
