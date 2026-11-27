"""Organization discovery for a server-verified identity."""
from workspace_security.identity import VerifiedIdentity


async def list_organizations(connection, identity: VerifiedIdentity):
    if not isinstance(identity, VerifiedIdentity):
        raise ValueError('A verified identity is required')
    rows = await connection.fetch('''
        SELECT o.id, o.name, m.role FROM workspace_organizations AS o
        JOIN workspace_memberships AS m ON m.organization_id = o.id
        JOIN workspace_users AS u ON u.id = m.user_id
        WHERE u.identity_issuer = $1 AND u.identity_subject = $2
        ORDER BY o.name, o.id
    ''', identity.issuer, identity.subject)
    return [dict(row) for row in rows]
