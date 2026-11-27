# Hosted workspace preview

The signed-in workspace is experimental and supports organization discovery
and account creation/listing only. Workflows in the public demo are separate;
they are not yet authenticated workspace workflows. Use fictional data only.

The browser client supports Keycloak authorization code + PKCE. In development
it still uses your configured local Keycloak issuer. A future hosted workspace
requires a separate HTTPS service, a reachable HTTPS Keycloak instance, its own
public client with exact redirect URI and allowed web origin, and a PostgreSQL
runtime account with narrowly scoped privileges. Register `<workspace origin>/workspace-app`
as the redirect URI; the token must include the API-specific audience. Never
put client secrets or database credentials in the browser configuration.

An operator would set `WORKSPACE_ENABLED=true`,
`WORKSPACE_HOSTED_UI_ENABLED=true`, `WORKSPACE_OIDC_ISSUER`,
`WORKSPACE_OIDC_JWKS_URL`, `WORKSPACE_OIDC_AUDIENCE`,
`WORKSPACE_OIDC_CLIENT_ID` and `WORKSPACE_DATABASE_URL` on the *separate*
workspace service. `PUBLIC_DEMO=true` always disables the workspace. In hosted
workspace mode legacy demo routes are unavailable and `/` redirects to the
workspace. The `/workspace-config` response contains only issuer and public
client ID, never the database URL or other secrets. An issuer must use HTTPS
except explicitly enabled local development. The service must itself use HTTPS.

Do not enable a hosted workspace for customer data yet. The current database
role guard cannot verify safe grants or policy definitions, its membership lock
requires privileges that need a reviewed least-privilege design, and protected
workflow operations and member administration are not implemented. Secrets management, protection from unauthenticated abuse, production recovery,
and end-to-end hosted identity and isolation tests are also unfinished. The
authenticated workspace rate limit is backed by the workspace database. The public demo can stay
online separately in its existing mode.
