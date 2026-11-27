-- Defense in depth for tenant-owned records. The application sets the
-- organization context after checking membership, inside the same transaction.
-- The application role must not be a superuser or have BYPASSRLS.
ALTER TABLE workspace_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_accounts FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_accounts_org_policy ON workspace_accounts
    USING (organization_id::text = current_setting('app.organization_id', true))
    WITH CHECK (organization_id::text = current_setting('app.organization_id', true));

ALTER TABLE workspace_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_contacts FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_contacts_org_policy ON workspace_contacts
    USING (organization_id::text = current_setting('app.organization_id', true))
    WITH CHECK (organization_id::text = current_setting('app.organization_id', true));

ALTER TABLE workspace_deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_deals FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_deals_org_policy ON workspace_deals
    USING (organization_id::text = current_setting('app.organization_id', true))
    WITH CHECK (organization_id::text = current_setting('app.organization_id', true));

ALTER TABLE workspace_workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_workflow_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_runs_org_policy ON workspace_workflow_runs
    USING (organization_id::text = current_setting('app.organization_id', true))
    WITH CHECK (organization_id::text = current_setting('app.organization_id', true));

ALTER TABLE workspace_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY workspace_audit_org_policy ON workspace_audit_events
    USING (organization_id::text = current_setting('app.organization_id', true))
    WITH CHECK (organization_id::text = current_setting('app.organization_id', true));
