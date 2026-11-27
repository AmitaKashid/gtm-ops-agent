-- One fixed-window counter per verified identity. No access tokens are stored.
CREATE TABLE workspace_rate_limits (
    principal_hash TEXT PRIMARY KEY CHECK (length(principal_hash) = 64),
    window_start TIMESTAMPTZ NOT NULL,
    request_count INTEGER NOT NULL CHECK (request_count > 0)
);
