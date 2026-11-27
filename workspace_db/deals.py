"""Deal operations require a verified identity and a tenant-scoped transaction."""
from uuid import uuid4

from workspace_security.authorization import Permission, require_membership


class AccountNotFound(Exception):
    pass


class TooManyDeals(Exception):
    pass


async def list_deals(connection, identity, organization_id):
    async with connection.transaction():
        await require_membership(connection, identity, organization_id, Permission.READ)
        await connection.execute("SELECT set_config('app.organization_id', $1, true)", str(organization_id))
        rows = await connection.fetch('''
            SELECT d.id, d.name, d.stage, d.owner_name, d.deal_value,
                   d.contact_email, d.contact_phone, d.last_contact_date,
                   d.stage_changed_date, d.account_id, a.name AS company
            FROM workspace_deals d JOIN workspace_accounts a
              ON a.organization_id = d.organization_id AND a.id = d.account_id
            WHERE d.organization_id = $1 ORDER BY d.created_at DESC, d.id DESC LIMIT 101
        ''', organization_id)
        if len(rows) > 100:
            raise TooManyDeals()
        return [dict(row) for row in rows]


async def create_deal(connection, identity, organization_id, data):
    async with connection.transaction():
        await require_membership(connection, identity, organization_id, Permission.WRITE)
        await connection.execute("SELECT set_config('app.organization_id', $1, true)", str(organization_id))
        # Serialize creation per organization so concurrent requests respect the preview limit.
        await connection.execute('SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))', str(organization_id))
        count = await connection.fetchval('SELECT count(*) FROM workspace_deals WHERE organization_id = $1', organization_id)
        if count >= 100:
            raise TooManyDeals()
        company = await connection.fetchval('''
            SELECT name FROM workspace_accounts WHERE organization_id = $1 AND id = $2
        ''', organization_id, data.account_id)
        if company is None:
            raise AccountNotFound()
        actor = await connection.fetchval('''
            SELECT id FROM workspace_users WHERE identity_issuer = $1 AND identity_subject = $2
        ''', identity.issuer, identity.subject)
        deal_id = uuid4()
        await connection.execute('''
            INSERT INTO workspace_deals
              (organization_id, id, account_id, name, stage, owner_name, deal_value,
               contact_email, contact_phone, last_contact_date, stage_changed_date)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ''', organization_id, deal_id, data.account_id, data.name, data.stage, data.owner_name,
            data.deal_value, data.contact_email, data.contact_phone,
            data.last_contact_date, data.stage_changed_date)
        await connection.execute('''
            INSERT INTO workspace_audit_events
              (organization_id, id, actor_id, action, object_type, object_id)
            VALUES ($1,$2,$3,'deal.created','deal',$4)
        ''', organization_id, uuid4(), actor, deal_id)
        return {'id': deal_id, 'company': company, **data.model_dump()}
