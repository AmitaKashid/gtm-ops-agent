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

## Dedicated runtime role (experimental)

`python -m workspace_db.runtime_grants --role gtm_workspace_app` adds only the
privileges currently required for organization discovery, account listing and
creation, and audit inserts to an existing dedicated login. Create that login
separately with a strong private password; do not reuse the migration owner.
Set `WORKSPACE_ADMIN_DATABASE_URL` privately to the owner connection. The
command does not create roles or remove inherited privileges. Never put the
admin URL in the running API service. The API uses `WORKSPACE_DATABASE_URL`.

For production mode, the role guard rejects schema creation, administrative
roles, bypass/ownership, membership role changes, and update or delete of
protected records. Existing `PUBLIC` or inherited grants may cause rejection.
The runtime has read access to workspace organization/user/membership metadata,
and can set the organization context itself: the checks are defense in depth,
not a security boundary against arbitrary SQL using a stolen database password.
The API must continue to verify identity and membership on every operation.
Policy definitions and all possible database grants are not fully verified.
Run the PostgreSQL integration suite against a disposable test database before
using this setup. It creates and drops a uniquely named database and role and
requires the test account to have CREATEDB and CREATEROLE privileges.

`python -m workspace_db.bootstrap_hosted` is a manually invoked operator tool
for creating the initial organization and owner from an existing Keycloak user
subject. It requires a remote database URL with `sslmode=verify-full` in
`WORKSPACE_ADMIN_DATABASE_URL` and an HTTPS identity issuer. It refuses to
promote an existing non-owner or add another owner to an occupied organization.
The tool does not expose an API endpoint, create Keycloak users, or implement
member invitations. Store the admin URL only in a secure operator environment.

## Shared request limit

Hosted workspace requests with a verified identity use a PostgreSQL fixed
one-minute window, default 60 requests per identity. Set
`WORKSPACE_RATE_LIMIT_PER_MINUTE` between 1 and 10000. This limit is shared by
instances using the same database. It does not stop unauthenticated traffic
before JWT validation or replace edge abuse controls. The rate-limit table
stores a SHA-256 identity key, not access tokens. Rows persist until an operator
removes them; define retention for your environment. Apply all migrations and
re-run the runtime-grants command before deploying this version.
