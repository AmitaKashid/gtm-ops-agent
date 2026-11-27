-- Additional fields for organization-scoped CRM hygiene scans.
ALTER TABLE workspace_deals
    ADD COLUMN owner_name TEXT,
    ADD COLUMN deal_value NUMERIC(14, 2),
    ADD COLUMN contact_email TEXT,
    ADD COLUMN contact_phone TEXT,
    ADD COLUMN last_contact_date DATE,
    ADD COLUMN stage_changed_date DATE;
