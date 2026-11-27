"""Fail-closed checks for the database role used by protected workspace routes."""

PROTECTED_TABLES = (
    'workspace_accounts', 'workspace_contacts', 'workspace_deals',
    'workspace_workflow_runs', 'workspace_audit_events',
)


class UnsafeDatabaseRole(Exception):
    pass


async def require_safe_database_role(connection):
    role = await connection.fetchrow('''
        SELECT current_user = session_user AS direct_login,
               EXISTS (
                 SELECT 1 FROM pg_roles AS r
                 WHERE (r.rolsuper OR r.rolbypassrls)
                   AND pg_has_role(current_user, r.oid, 'MEMBER')
               ) AS can_bypass
    ''')
    if not role or not role['direct_login'] or role['can_bypass']:
        raise UnsafeDatabaseRole('Workspace database role is unsafe')
    rows = await connection.fetch('''
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
               pg_has_role(current_user, c.relowner, 'MEMBER') AS can_own
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = current_schema() AND c.relname = ANY($1::text[])
          AND c.relkind IN ('r', 'p')
    ''', list(PROTECTED_TABLES))
    if len(rows) != len(PROTECTED_TABLES):
        raise UnsafeDatabaseRole('Workspace row policies are not installed')
    if any(not row['relrowsecurity'] or not row['relforcerowsecurity'] or row['can_own'] for row in rows):
        raise UnsafeDatabaseRole('Workspace row policies or database role are unsafe')
