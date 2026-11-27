# Workspace identity verification primitive

`verify_access_token` checks an RS256 JWT signature with keys from an explicitly
configured HTTPS JWKS endpoint, plus issuer, audience, expiry, issued-at and
subject claims. It returns the issuer and subject, not a role or organization.
It does not install an authentication dependency or protect any routes.

For a future deployment, select a trusted identity provider that issues JWT
access tokens for a distinct API-specific audience. Do not use an OIDC ID token
as an API bearer token. This primitive does not check any provider-specific
`token_use`, scope, token revocation, or membership claims. Provider-specific
requirements and tests are needed before connecting it to application routes.

Authorization must look up the verified identity and current organization
membership server-side on every relevant request. Never trust a role or
organization solely supplied by a caller. Use HTTPS; do not log tokens.

`require_membership` implements a database membership lookup and role checks
for future callers. It requires an existing transaction; the caller must keep
the protected operation in that same transaction. No routes use it yet.

This is a development foundation, not a production-ready login system. No
provider is configured and there is no browser login, onboarding, account
lifecycle, or organization isolation until subsequent changes are implemented
and tested against PostgreSQL.

## Protected account API (opt-in development only)

The `/workspace/organizations/{organization_id}/accounts` GET and POST
routes are unavailable unless `WORKSPACE_ENABLED=true` and `PUBLIC_DEMO` is
not `true`. They require an RS256 bearer access token and a matching database
membership. Configure `WORKSPACE_OIDC_ISSUER`, `WORKSPACE_OIDC_AUDIENCE`,
`WORKSPACE_OIDC_JWKS_URL` and `WORKSPACE_DATABASE_URL` privately. The issuer
and JWKS endpoint currently require HTTPS. Browser cross-origin requests must
also be explicitly allowed in `CORS_ALLOWED_ORIGINS`.

There is no browser login, user provisioning flow, or identity provider setup
in this patch. The previous unprotected demo routes remain separate and are
not tenant-aware. Do not set `WORKSPACE_ENABLED` on the public demo or put
real customer data into it. Further work is required for a production identity
provider, token semantics and revocation, database permissions/row security,
backups, and operational controls.

## Local Keycloak development server

`docker-compose.keycloak.yml` is a local-only development service bound to
127.0.0.1:8088. Set `KEYCLOAK_ADMIN_USER` and `KEYCLOAK_ADMIN_PASSWORD`
privately in your terminal before starting it. Never reuse these development
credentials; never put them in source control, a screenshot, or chat. The
credentials bootstrap the admin only when the Keycloak database is first
created. The named volume keeps local development data between restarts.

For a local API process only, `APP_ENV=development` together with
`WORKSPACE_ALLOW_INSECURE_LOCAL_OIDC=true` permits HTTP issuer and JWKS URLs
only for localhost, 127.0.0.1, or ::1. Start the API on 127.0.0.1. Never use
this option with a public server. The public demo disallows workspace access.

Keycloak still needs a realm, public browser client, separate API audience
mapper and test user. No automatic realm or user provisioning or browser
login is implemented yet. Keycloak must add the API-specific audience to the
access token (not the ID token); verify token semantics for your configuration.
