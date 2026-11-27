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
               ) AS can_bypass,
               EXISTS (SELECT 1 FROM pg_roles AS r WHERE (r.rolcreaterole OR r.rolcreatedb OR r.rolreplication)
                   AND pg_has_role(current_user, r.oid, 'MEMBER')) AS can_administer,
               has_schema_privilege(current_user, current_schema(), 'CREATE') AS can_create_in_schema,
               has_table_privilege(current_user, 'workspace_memberships', 'INSERT, DELETE, TRUNCATE, TRIGGER, REFERENCES')
                 OR has_column_privilege(current_user, 'workspace_memberships', 'organization_id', 'UPDATE')
                 OR has_column_privilege(current_user, 'workspace_memberships', 'user_id', 'UPDATE')
                 OR has_column_privilege(current_user, 'workspace_memberships', 'role', 'UPDATE') AS can_modify_members,
               has_table_privilege(current_user, 'workspace_users', 'INSERT, DELETE, TRUNCATE, TRIGGER, REFERENCES')
                 OR has_any_column_privilege(current_user, 'workspace_users', 'UPDATE')
                 OR has_table_privilege(current_user, 'workspace_organizations', 'INSERT, DELETE, TRUNCATE, TRIGGER, REFERENCES')
                 OR has_any_column_privilege(current_user, 'workspace_organizations', 'UPDATE')
                 AS can_modify_identity,
               EXISTS (SELECT 1 FROM unnest(ARRAY['workspace_accounts', 'workspace_contacts', 'workspace_deals', 'workspace_workflow_runs', 'workspace_audit_events']) AS t(name)
                 WHERE has_table_privilege(current_user, t.name, 'DELETE, TRUNCATE, TRIGGER, REFERENCES')
                    OR has_any_column_privilege(current_user, t.name, 'UPDATE')) AS can_modify_protected
    ''')
    if (not role or not role['direct_login'] or role['can_bypass'] or role['can_create_in_schema']
            or role['can_administer'] or role['can_modify_members'] or role['can_modify_identity']
            or role['can_modify_protected']):
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
