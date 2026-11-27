"""Shared fixed-window limit for authenticated workspace requests."""
import hashlib
import os


class RateLimitConfigurationError(Exception):
    pass


def configured_limit():
    try:
        limit = int(os.getenv('WORKSPACE_RATE_LIMIT_PER_MINUTE', '60'))
    except ValueError:
        raise RateLimitConfigurationError('Invalid workspace rate limit') from None
    if not 1 <= limit <= 10000:
        raise RateLimitConfigurationError('Invalid workspace rate limit')
    return limit


async def consume_workspace_request(connection, identity, limit):
    # Length-prefixing avoids collisions between issuer/subject tuples.
    value = f'{len(identity.issuer)}:{identity.issuer}{identity.subject}'
    key = hashlib.sha256(value.encode('utf-8')).hexdigest()
    result = await connection.fetchval('''
        INSERT INTO workspace_rate_limits (principal_hash, window_start, request_count)
        VALUES ($1, date_trunc('minute', now()), 1)
        ON CONFLICT (principal_hash) DO UPDATE
        SET window_start = date_trunc('minute', now()),
            request_count = CASE
                WHEN workspace_rate_limits.window_start < date_trunc('minute', now()) THEN 1
                ELSE workspace_rate_limits.request_count + 1 END
        WHERE workspace_rate_limits.window_start < date_trunc('minute', now())
           OR workspace_rate_limits.request_count < $2
        RETURNING request_count
    ''', key, limit)
    return result is not None
