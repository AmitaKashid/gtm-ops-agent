from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from workspace_security.identity import IdentitySettings
from api.middleware.logging import RequestLoggingMiddleware
from api.middleware.public_demo import PublicDemoMiddleware
from api.middleware.hosted_workspace import HostedWorkspaceBoundary
from api.routers import crm, leads, emails, meetings, competitors, hr_onboarding, workspace


app = FastAPI(
    title="GTM Ops Agent",
    description="API for sales and business operations workflows.",
    version="0.1.0",
)

def allowed_origins() -> list[str]:
    """Return explicit browser origins from configuration."""
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8080,http://localhost:8080")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app.add_middleware(PublicDemoMiddleware)
app.add_middleware(HostedWorkspaceBoundary)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(crm.router)
app.include_router(leads.router)
app.include_router(emails.router)
app.include_router(meetings.router)
app.include_router(competitors.router)
app.include_router(hr_onboarding.router)
app.include_router(workspace.router)

_DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "docs"
_WORKSPACE_UI_DIR = Path(__file__).resolve().parent.parent / "workspace_ui"


def local_workspace_ui_enabled():
    return (
        os.getenv('APP_ENV', '').lower() == 'development'
        and os.getenv('WORKSPACE_ENABLED', '').lower() == 'true'
        and os.getenv('PUBLIC_DEMO', '').lower() != 'true'
    )


def workspace_ui_enabled():
    if os.getenv('PUBLIC_DEMO', '').lower() == 'true' or os.getenv('WORKSPACE_ENABLED', '').lower() != 'true':
        return False
    return local_workspace_ui_enabled() or os.getenv('WORKSPACE_HOSTED_UI_ENABLED', '').lower() == 'true'


@app.get('/workspace-app', include_in_schema=False)
async def workspace_dashboard():
    if not workspace_ui_enabled():
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(_WORKSPACE_UI_DIR / 'index.html', headers={'Cache-Control': 'no-store'})


@app.get('/workspace-app.js', include_in_schema=False)
async def workspace_dashboard_script():
    if not workspace_ui_enabled():
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(_WORKSPACE_UI_DIR / 'app.js', media_type='text/javascript', headers={'Cache-Control': 'no-store'})


@app.get('/workspace-config', include_in_schema=False)
async def workspace_browser_config():
    if not workspace_ui_enabled():
        raise HTTPException(status_code=404, detail='Not found')
    issuer = os.getenv('WORKSPACE_OIDC_ISSUER', '')
    client_id = os.getenv('WORKSPACE_OIDC_CLIENT_ID', 'gtm-workspace-web' if local_workspace_ui_enabled() else '')
    try:
        IdentitySettings(issuer, os.getenv('WORKSPACE_OIDC_AUDIENCE', ''), os.getenv('WORKSPACE_OIDC_JWKS_URL', ''),
                         allow_insecure_loopback=local_workspace_ui_enabled() and os.getenv('WORKSPACE_ALLOW_INSECURE_LOCAL_OIDC', '').lower() == 'true')
        if not client_id or len(client_id) > 200 or any(ch.isspace() for ch in client_id):
            raise ValueError('Invalid client ID')
    except ValueError:
        raise HTTPException(status_code=503, detail='Workspace sign-in is not configured') from None
    return JSONResponse({'issuer': issuer.rstrip('/'), 'client_id': client_id}, headers={'Cache-Control': 'no-store'})


@app.get("/", include_in_schema=False)
async def dashboard():
    """Serve the dashboard at the backend's own address."""
    if (workspace_ui_enabled() and not local_workspace_ui_enabled()
            and os.getenv('WORKSPACE_HOSTED_UI_ENABLED', '').lower() == 'true'):
        return RedirectResponse('/workspace-app', status_code=307)
    return FileResponse(_DASHBOARD_DIR / "index.html")


@app.get("/api-config.js", include_in_schema=False)
async def dashboard_config():
    return FileResponse(_DASHBOARD_DIR / "api-config.js", media_type="text/javascript")


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Confirm that the API process can respond to requests."""
    return HealthResponse(
        status="healthy",
        service="gtm-ops-agent",
        version=app.version,
    )
