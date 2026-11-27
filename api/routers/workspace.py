"""Authenticated workspace endpoints; disabled unless explicitly configured."""
import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from workspace_db.accounts import create_account, list_accounts
from workspace_db.connection import DatabaseConfigurationError, prepare_database_url
from workspace_db.deals import AccountNotFound, TooManyDeals, create_deal, list_deals
from workspace_db.organizations import list_organizations
from workspace_security.authorization import AccessDenied
from workspace_security.authorization import Permission, require_membership
from workspace_security.database_guard import UnsafeDatabaseRole, require_safe_database_role
from workspace_security.identity import IdentitySettings, InvalidAccessToken, verify_access_token
from workspace_security.rate_limit import RateLimitConfigurationError, configured_limit, consume_workspace_request
from api.routers.crm import CRMRequest, CRMResponse, DealInput, analyze_crm

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/workspace', tags=['Workspace'])
bearer = HTTPBearer(auto_error=False)


async def workspace_identity(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if os.getenv('PUBLIC_DEMO', '').lower() == 'true' or os.getenv('WORKSPACE_ENABLED', '').lower() != 'true':
        raise HTTPException(status_code=503, detail='Workspace is not enabled')
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    try:
        allow_local_http = (
            os.getenv('APP_ENV', '').lower() == 'development'
            and os.getenv('WORKSPACE_ALLOW_INSECURE_LOCAL_OIDC', '').lower() == 'true'
        )
        settings = IdentitySettings(os.getenv('WORKSPACE_OIDC_ISSUER', ''), os.getenv('WORKSPACE_OIDC_AUDIENCE', ''), os.getenv('WORKSPACE_OIDC_JWKS_URL', ''), allow_insecure_loopback=allow_local_http)
    except ValueError:
        logger.error('Workspace identity configuration is invalid')
        raise HTTPException(status_code=503, detail='Workspace identity is not configured') from None
    try:
        return await asyncio.to_thread(verify_access_token, credentials.credentials, settings)
    except InvalidAccessToken:
        raise HTTPException(status_code=401, detail='Invalid access token', headers={'WWW-Authenticate': 'Bearer'}) from None


async def workspace_connection(identity=Depends(workspace_identity)):
    url = os.getenv('WORKSPACE_DATABASE_URL')
    if not url:
        raise HTTPException(status_code=503, detail='Workspace database is not configured')
    try:
        dsn = prepare_database_url(url, require_verified_tls=os.getenv('APP_ENV', '').lower() != 'development')
        conn = await asyncpg.connect(dsn, timeout=10)
    except (OSError, asyncpg.PostgresError, TimeoutError, DatabaseConfigurationError):
        logger.error('Workspace database connection failed')
        raise HTTPException(status_code=503, detail='Workspace database unavailable') from None
    try:
        require_guard = (os.getenv('APP_ENV', '').lower() != 'development' or
                         os.getenv('WORKSPACE_REQUIRE_DB_RLS', '').lower() == 'true')
        if require_guard:
            try:
                await require_safe_database_role(conn)
            except (UnsafeDatabaseRole, asyncpg.PostgresError):
                logger.error('Workspace database security check failed')
                raise HTTPException(status_code=503, detail='Workspace database security is not configured') from None
            try:
                allowed = await consume_workspace_request(conn, identity, configured_limit())
            except (RateLimitConfigurationError, asyncpg.PostgresError):
                logger.error('Workspace rate limit is unavailable')
                raise HTTPException(status_code=503, detail='Workspace rate limit is unavailable') from None
            if not allowed:
                raise HTTPException(status_code=429, detail='Workspace request limit reached', headers={'Retry-After': '60'})
        yield conn
    finally:
        await conn.close()


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class Account(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class Organization(BaseModel):
    id: UUID
    name: str
    role: str


class DealCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    account_id: UUID
    name: str = Field(min_length=1, max_length=255)
    stage: str = Field(min_length=1, max_length=100)
    owner_name: str = Field(min_length=1, max_length=120)
    deal_value: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2, allow_inf_nan=False)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_phone: str | None = Field(default=None, max_length=50)
    last_contact_date: date
    stage_changed_date: date


class Deal(BaseModel):
    id: UUID
    account_id: UUID
    name: str
    stage: str
    owner_name: str | None = None
    deal_value: Decimal | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    last_contact_date: date | None = None
    stage_changed_date: date | None = None
    company: str


@router.get('/organizations', response_model=list[Organization])
async def read_organizations(identity=Depends(workspace_identity), conn=Depends(workspace_connection)):
    return await list_organizations(conn, identity)


@router.get('/organizations/{organization_id}/accounts', response_model=list[Account])
async def read_accounts(organization_id: UUID, identity=Depends(workspace_identity), conn=Depends(workspace_connection)):
    try:
        return await list_accounts(conn, identity, organization_id)
    except AccessDenied:
        raise HTTPException(status_code=403, detail='Access denied') from None


@router.post('/organizations/{organization_id}/accounts', response_model=Account, status_code=status.HTTP_201_CREATED)
async def add_account(organization_id: UUID, body: AccountCreate, identity=Depends(workspace_identity), conn=Depends(workspace_connection)):
    try:
        return await create_account(conn, identity, organization_id, body.name)
    except AccessDenied:
        raise HTTPException(status_code=403, detail='Access denied') from None
    except ValueError:
        raise HTTPException(status_code=422, detail='Account name must contain 1 to 255 characters') from None


@router.post('/organizations/{organization_id}/crm/sample-scan', response_model=CRMResponse)
async def scan_sample_crm(organization_id: UUID, identity=Depends(workspace_identity), conn=Depends(workspace_connection)):
    """Run a deterministic scan on fictional data after checking membership.

    This endpoint does not read an organization's CRM or send notifications.
    It accepts no deal data and does not persist the results.
    """
    today = date.today()
    old = (today - timedelta(days=61)).isoformat()
    request = CRMRequest(scan_date=today.isoformat(), deals=[DealInput(
        deal_id='SAMPLE-001', deal_name='Example subscription', company='Example Company',
        owner='Sample owner', stage='Proposal', deal_value=10000,
        contact_email='sample@example.com', contact_phone=None,
        last_contact_date=old, stage_changed_date=old,
    )])
    try:
        async with conn.transaction():
            await require_membership(conn, identity, organization_id, Permission.READ)
            return await analyze_crm(request)
    except AccessDenied:
        raise HTTPException(status_code=403, detail='Access denied') from None
    except HTTPException:
        logger.error('Workspace sample CRM scan failed')
        raise HTTPException(status_code=500, detail='CRM scan failed') from None


@router.get('/organizations/{organization_id}/deals', response_model=list[Deal])
async def read_deals(organization_id: UUID, identity=Depends(workspace_identity), conn=Depends(workspace_connection)):
    try:
        return await list_deals(conn, identity, organization_id)
    except AccessDenied:
        raise HTTPException(status_code=403, detail='Access denied') from None
    except TooManyDeals:
        raise HTTPException(status_code=409, detail='This preview supports up to 100 deals per organization') from None


@router.post('/organizations/{organization_id}/deals', response_model=Deal, status_code=201)
async def add_deal(organization_id: UUID, body: DealCreate, identity=Depends(workspace_identity), conn=Depends(workspace_connection)):
    try:
        return await create_deal(conn, identity, organization_id, body)
    except AccessDenied:
        raise HTTPException(status_code=403, detail='Access denied') from None
    except AccountNotFound:
        raise HTTPException(status_code=404, detail='Account not found') from None
    except TooManyDeals:
        raise HTTPException(status_code=409, detail='This preview supports up to 100 deals per organization') from None


@router.post('/organizations/{organization_id}/crm/scan', response_model=CRMResponse)
async def scan_workspace_crm(organization_id: UUID, identity=Depends(workspace_identity), conn=Depends(workspace_connection)):
    try:
        deals = await list_deals(conn, identity, organization_id)
    except AccessDenied:
        raise HTTPException(status_code=403, detail='Access denied') from None
    except TooManyDeals:
        raise HTTPException(status_code=409, detail='This preview supports up to 100 deals per scan') from None
    if not deals:
        raise HTTPException(status_code=409, detail='Add a deal before starting a scan')
    items = [DealInput(
        deal_id=str(d['id']), deal_name=d['name'], company=d['company'], owner=d['owner_name'] or '',
        stage=d['stage'], deal_value=d['deal_value'], contact_email=d['contact_email'],
        contact_phone=d['contact_phone'],
        last_contact_date=d['last_contact_date'].isoformat() if d['last_contact_date'] else None,
        stage_changed_date=d['stage_changed_date'].isoformat() if d['stage_changed_date'] else None,
    ) for d in deals]
    try:
        return await analyze_crm(CRMRequest(deals=items))
    except HTTPException:
        logger.error('Workspace CRM scan failed')
        raise HTTPException(status_code=500, detail='CRM scan failed') from None
