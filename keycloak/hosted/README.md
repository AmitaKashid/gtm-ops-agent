# Hosted Keycloak preview

This image is an unverified hosted preview, not a production deployment. The
public demo and the signed-in workspace remain separate. Use fictional data.
Build from the repository root with `docker build -f keycloak/hosted/Dockerfile .`.
The server starts in production mode with a public client that requires PKCE,
and imports the realm only when it does not already exist.

Configure an HTTPS reverse proxy and its trusted headers for the actual host.
Set `KC_HOSTNAME` to the exact HTTPS identity-service origin, `KC_PROXY_HEADERS`
to the value required by the trusted proxy, `WORKSPACE_ORIGIN` to the exact
HTTPS workspace-service origin, and `PORT=8080` for the hosting service. No
wildcards or trailing slash should be used for `WORKSPACE_ORIGIN`. Configure
`KC_DB_URL`, `KC_DB_USERNAME`, `KC_DB_PASSWORD`, `KC_BOOTSTRAP_ADMIN_USERNAME`
and `KC_BOOTSTRAP_ADMIN_PASSWORD` as private hosting environment variables.
Use an isolated PostgreSQL database and a dedicated identity-service role. Do
not configure the public demo's service with these variables. Configure and test
certificate and hostname verification for the database connection before use.
Never put credentials into the repository, realm JSON, or chat.

The first startup creates an admin from the bootstrap environment variables.
After secure first access, create a non-temporary administrator and remove the
bootstrap credentials following the Keycloak documentation. Realm import on
startup skips an existing realm; changing the environment later does not update
its client redirect URI or origins. No users are pre-created, registration is
disabled, and member invitations are not implemented. Protect the admin
console; verify proxy configuration, TLS, backup/restore, resource limits and
identity isolation before deployment. Render's free service can sleep and
its workspace has a shared monthly free-hour allowance.
