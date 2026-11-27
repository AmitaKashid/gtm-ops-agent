# Workspace database operations

These instructions cover local development only. This project is not yet a
production-ready multi-tenant system. The public demo remains separate and
should not contain real customer data.

## Migration and row policies

Use the local database owner and explicitly set `DATABASE_URL` before running
`python -m workspace_db.migrate`. Migration 002 adds row policies to accounts,
contacts, deals, workflow runs, and audit events. Account operations set the
organization context after checking membership inside the same transaction.
Organizations, users, and memberships are not covered by those policies.

Superusers and BYPASSRLS roles bypass row policies. The local Compose `gtmuser`
is a development superuser, so it does not demonstrate production isolation.
CI includes a test that creates an isolated non-bypass role and checks the
policies. That test needs permission to create and drop a temporary role, and
must run only against a dedicated disposable test database.

The API checks role privileges and row-security flags when APP_ENV is not
`development`, or when WORKSPACE_REQUIRE_DB_RLS=true. The check does not verify
policy definitions, grants, safe SQL construction, identity configuration, or
all tables. The application sets the row context, so this is defense in depth,
not authorization against arbitrary SQL access. The `FOR SHARE` membership
lookup requires appropriate PostgreSQL privileges; a safe narrowly scoped
runtime role design is still needed before production. Do not enable a public
workspace simply because the guard passes.

## Local backup and restore drill

With local Docker Compose PostgreSQL running, create a new backup file:

```cmd
.venv\Scripts\python.exe -m workspace_db.backup_local backup --output backups\workspace-dev.dump
```

To verify it, restore into a randomly named temporary database and query the
migration table. The verification removes only the temporary database it
successfully created:

```cmd
.venv\Scripts\python.exe -m workspace_db.backup_local verify --file backups\workspace-dev.dump
```

This does not overwrite `gtmops`. Backup files can contain all local database
content; do not commit or share them. Store them securely and remove old local
copies according to your own retention requirements. File permissions differ
by operating system. This utility does not provide encryption, offsite storage,
a schedule, role/Keycloak backup, or production disaster recovery.
