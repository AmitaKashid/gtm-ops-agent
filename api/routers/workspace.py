"""Authenticated workspace endpoints; disabled unless explicitly configured."""
import asyncio
import logging
import os
from datetime import datetime
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from workspace_db.accounts import create_account, list_accounts
from workspace_db.connection import DatabaseConfigurationError, prepare_database_url
from workspace_db.organizations import list_organizations
from workspace_security.authorization import AccessDenied
from workspace_security.database_guard import UnsafeDatabaseRole, require_safe_database_role
from workspace_security.identity import IdentitySettings, InvalidAccessToken, verify_access_token
from workspace_security.rate_limit import RateLimitConfigurationError, configured_limit, consume_workspace_request

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
