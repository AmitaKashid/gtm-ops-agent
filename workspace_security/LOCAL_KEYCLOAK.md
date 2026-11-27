# Local workspace development

This is an experimental local environment. It does not make the system
production-ready. Do not use real customer data. Bind both Keycloak and the API
to loopback only. The public Render service must remain in PUBLIC_DEMO mode.

## Start local Keycloak

Start Docker Desktop. In a Windows Command Prompt, set a unique local-only
bootstrap admin username and password privately in your shell. Do not commit,
print, screenshot or share these values. Then start the standalone service:

```cmd
set /p KEYCLOAK_ADMIN_USER=Choose local admin username:
set /p KEYCLOAK_ADMIN_PASSWORD=Choose local admin password:
docker compose -f docker-compose.keycloak.yml up -d
```

Command Prompt displays typed input for `set /p`; do not share that terminal
output. These credentials are only for this local development container.

Open http://127.0.0.1:8088 and sign in to the administration console. The
`gtm-dev` realm should be imported on first startup. If it already exists,
Keycloak skips import; verify the existing client and mapper manually rather
than deleting the volume or overwriting a realm. In `gtm-dev`, create a local
test user and set a test-only password. Copy the user's Keycloak ID from its
admin page. The realm has no pre-created user or password.

## Create a local organization

In another Command Prompt, in the project directory, start local PostgreSQL
and apply the migration if needed. Set these variables in that window:

```cmd
docker compose up -d postgres
set "APP_ENV=development"
set "PUBLIC_DEMO=false"
set "WORKSPACE_DATABASE_URL=postgresql://gtmuser:gtmpassword@127.0.0.1:5432/gtmops"
set "DATABASE_URL=postgresql://gtmuser:gtmpassword@127.0.0.1:5432/gtmops"
.venv\Scripts\python.exe -m workspace_db.migrate
```

Set `LOCAL_KEYCLOAK_USER_ID` to the test user's actual Keycloak ID, then:

```cmd
.venv\Scripts\python.exe -m workspace_db.bootstrap_local --organization-id 11111111-1111-4111-8111-111111111111 --name "Demo organization" --issuer http://127.0.0.1:8088/realms/gtm-dev --subject %LOCAL_KEYCLOAK_USER_ID%
```

This is a local-only bootstrap and refuses an existing organization with
another member; it cannot be used to silently promote an existing member.

## Start API and sign in

In the same API Command Prompt:

```cmd
set "WORKSPACE_ENABLED=true"
set "WORKSPACE_ALLOW_INSECURE_LOCAL_OIDC=true"
set "WORKSPACE_OIDC_ISSUER=http://127.0.0.1:8088/realms/gtm-dev"
set "WORKSPACE_OIDC_JWKS_URL=http://127.0.0.1:8088/realms/gtm-dev/protocol/openid-connect/certs"
set "WORKSPACE_OIDC_AUDIENCE=gtm-workspace-api"
.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8010
```

Open http://127.0.0.1:8010/workspace-app and sign in with the Keycloak test
user. Access tokens stay in browser memory; reloading the page requires sign-in
again. Sign out in this app clears its local token but does not end the
Keycloak session. Account creation is available to owners/admins/members;
viewers can only read. The backend checks membership on each operation.

The GitHub Pages and Render demo do not become an authenticated workspace.
See HOSTED_PREVIEW.md for the hosted prototype and its limitations. Never enable
local HTTP identity on a public instance.
