-- New workspace tables are separate from the legacy demo tables.
-- UUIDs are created by the application, without requiring extensions.
CREATE TABLE workspace_organizations (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workspace_users (
    id UUID PRIMARY KEY,
    identity_issuer TEXT NOT NULL,
    identity_subject TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (identity_issuer, identity_subject)
);

CREATE TABLE workspace_memberships (
    organization_id UUID NOT NULL REFERENCES workspace_organizations(id),
    user_id UUID NOT NULL REFERENCES workspace_users(id),
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE workspace_accounts (
    organization_id UUID NOT NULL REFERENCES workspace_organizations(id),
    id UUID NOT NULL,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, id)
);

CREATE TABLE workspace_contacts (
    organization_id UUID NOT NULL,
    id UUID NOT NULL,
    account_id UUID NOT NULL,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, id),
    FOREIGN KEY (organization_id, account_id)
        REFERENCES workspace_accounts(organization_id, id)
);

CREATE TABLE workspace_deals (
    organization_id UUID NOT NULL,
    id UUID NOT NULL,
    account_id UUID NOT NULL,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 255),
    stage TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, id),
    FOREIGN KEY (organization_id, account_id)
        REFERENCES workspace_accounts(organization_id, id)
);

CREATE TABLE workspace_workflow_runs (
    organization_id UUID NOT NULL REFERENCES workspace_organizations(id),
    id UUID NOT NULL,
    workflow TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    PRIMARY KEY (organization_id, id)
);

CREATE TABLE workspace_audit_events (
    organization_id UUID NOT NULL REFERENCES workspace_organizations(id),
    id UUID NOT NULL,
    actor_id UUID,
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, id),
    FOREIGN KEY (organization_id, actor_id)
        REFERENCES workspace_memberships(organization_id, user_id)
);

CREATE INDEX workspace_runs_org_created_idx ON workspace_workflow_runs (organization_id, created_at DESC);
CREATE INDEX workspace_audit_org_created_idx ON workspace_audit_events (organization_id, created_at DESC);
