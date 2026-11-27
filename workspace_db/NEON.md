# Neon setup for the workspace

This creates an experimental workspace database for fictional data only. It is
not a production-readiness claim and does not deploy Keycloak or the API.
The public Render demo remains separate from this database.

1. Create a Neon project and copy the **direct, non-pooled** connection string
   privately. Store the administrator string as `WORKSPACE_ADMIN_DATABASE_URL`
   only on the operator machine. Never commit it, share it, or set it as the
   running web service's runtime URL.
2. The Python driver used here does not support libpq's `channel_binding` URL
   parameter. Remove that parameter from the copy used by this app, and replace
   `sslmode=require` with `sslmode=verify-full`. The app supplies the installed
   `certifi` CA bundle to asyncpg unless `sslrootcert` names a CA bundle file.
   This uses certificate and hostname verification; it does not provide SCRAM
   channel binding. The API rejects other TLS modes outside development.
3. Set `DATABASE_URL` privately to the admin URL and run
   `python -m workspace_db.migrate`. Back up an existing database first. Do not
   run migration commands against a database whose data you have not reviewed.
4. Use SQL to create a dedicated application login, not a console-created admin
   role. Neon documents that console-created roles inherit neon_superuser. Use
   a unique strong password privately; do not paste it in chat or git. Then run
   `python -m workspace_db.runtime_grants --role <runtime_role>` with the admin
   URL set. The runtime role is intended to have only the documented grants.
5. Provision the first owner using `python -m workspace_db.bootstrap_hosted`
   with a real HTTPS Keycloak issuer and an existing user's immutable subject.
   This does not create a Keycloak user or invite members.
6. Configure the separate hosted workspace service with that **runtime** role's
   URL, never the administrator URL. See `workspace_security/HOSTED_PREVIEW.md`.

Verify migrations, restricted grants, runtime security checks, and sign-in on
an isolated test deployment before considering customer data. Current gaps
include browser-visible workflow integration, edge abuse controls, production
backups/recovery, and end-to-end hosted identity tests.
