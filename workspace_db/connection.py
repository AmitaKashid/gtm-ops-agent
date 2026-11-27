"""Connection configuration for workspace Postgres."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import certifi


class DatabaseConfigurationError(ValueError):
    """Invalid configuration; deliberately never includes the URL or password."""


def prepare_database_url(url, *, require_verified_tls=False):
    """Validate hosted TLS and supply an explicit CA bundle for asyncpg.

    asyncpg treats unknown URL parameters as PostgreSQL server settings. In
    particular it does not support libpq's channel_binding option here.
    Reject it rather than silently weakening a caller's requested protection.
    """
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {'postgres', 'postgresql'} or not parsed.hostname or parsed.fragment:
            raise DatabaseConfigurationError('Invalid PostgreSQL URL')
        if not require_verified_tls:
            return url
        items = parse_qsl(parsed.query, keep_blank_values=True)
        sslmodes = [value for key, value in items if key == 'sslmode']
        roots = [value for key, value in items if key == 'sslrootcert']
        if sslmodes != ['verify-full']:
            raise DatabaseConfigurationError('Hosted database requires sslmode=verify-full')
        if any(key == 'channel_binding' for key, _ in items):
            raise DatabaseConfigurationError('asyncpg does not support the channel_binding URL option; remove it and keep verified TLS')
        if len(roots) > 1 or (roots and (not roots[0] or roots[0] == 'system')):
            raise DatabaseConfigurationError('Provide a CA bundle file or omit sslrootcert')
        if not roots:
            items.append(('sslrootcert', certifi.where()))
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(items), ''))
    except ValueError as exc:
        if isinstance(exc, DatabaseConfigurationError):
            raise
        raise DatabaseConfigurationError('Invalid PostgreSQL URL') from None
