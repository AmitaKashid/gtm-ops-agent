"""Role-based membership checks for workspace operations.

Callers must hold the same database transaction through the protected action.
This module does not wire authorization into any endpoint.
"""
from enum import Enum
from uuid import UUID

from workspace_security.identity import VerifiedIdentity


class Permission(str, Enum):
    READ = 'read'
    WRITE = 'write'
    MANAGE_MEMBERS = 'manage_members'


_ALLOWED = {
    Permission.READ: frozenset({'owner', 'admin', 'member', 'viewer'}),
    Permission.WRITE: frozenset({'owner', 'admin', 'member'}),
    Permission.MANAGE_MEMBERS: frozenset({'owner', 'admin'}),
}


class AccessDenied(Exception):
    """Identity is not permitted to perform the requested operation."""


async def require_membership(connection, identity: VerifiedIdentity, organization_id: UUID, permission: Permission):
    """Check current membership and lock its row until the transaction ends.

    The caller MUST open a transaction and perform the protected operation in
    that same transaction. A FOR SHARE lock prevents membership changes from
    committing while that transaction is executing.
    """
    if not isinstance(identity, VerifiedIdentity) or not isinstance(organization_id, UUID) or not isinstance(permission, Permission):
        raise AccessDenied('Access denied')
    if not connection.is_in_transaction():
        raise RuntimeError('Membership checks require an active transaction')
    role = await connection.fetchval('''
        SELECT m.role
        FROM workspace_memberships AS m
        JOIN workspace_users AS u ON u.id = m.user_id
        WHERE m.organization_id = $1 AND u.identity_issuer = $2 AND u.identity_subject = $3
        FOR SHARE OF m
    ''', organization_id, identity.issuer, identity.subject)
    if role not in _ALLOWED[permission]:
        raise AccessDenied('Access denied')
    return role
