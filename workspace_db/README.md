# Workspace database foundation

This is an additive schema for future workspace features. The existing demo
continues to use its legacy tables. These tables are not connected to any
route, and their presence does not provide authentication or tenant isolation.
Application authorization and database policies must be implemented and
independently verified before storing real customer data.

## Local migration

Start the existing development PostgreSQL service with Docker Compose. In a
Windows Command Prompt, set the URL explicitly for this shell and run:

```cmd
docker compose up -d postgres
set "DATABASE_URL=postgresql://gtmuser:gtmpassword@127.0.0.1:5432/gtmops"
.venv\Scripts\python.exe -m workspace_db.migrate
```

Run the command a second time to check that it is idempotent. It uses a
transaction and a PostgreSQL advisory lock; each migration's SHA-256 checksum
is stored and checked. Never edit an applied SQL file; add a new version.
The sample credentials above are for local development only. Back up any
existing database and verify recovery before applying migrations there.

No frontend, authentication, audit capture, database backup, or storage for
external credentials is implemented by this foundation alone.

## PostgreSQL integration tests

Run tests against a dedicated, disposable PostgreSQL database. Set
`TEST_DATABASE_URL` to its connection URL and run
`python -m pytest tests/test_workspace_postgres.py -v`. Tests create and remove
randomly named schemas. If the variable is absent, these integration tests skip;
CI starts a PostgreSQL service and runs them.

The cross-organization foreign key test covers one data-integrity constraint.
It does not prove authorization or row-level isolation: the application has
not implemented either yet.

`workspace_db.accounts` contains internal account operations that check
membership and create an audit event in the same transaction. Callers must
supply an identity verified by a trusted provider. These functions are not
connected to HTTP routes and do not replace authentication or database row
security.
