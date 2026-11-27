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

This is a development foundation, not a production-ready login system. No
provider is configured and there is no browser login, onboarding, account
lifecycle, or organization isolation until subsequent changes are implemented
and tested against PostgreSQL.
