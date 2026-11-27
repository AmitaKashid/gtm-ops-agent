from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from api.middleware.logging import RequestLoggingMiddleware
from api.middleware.public_demo import PublicDemoMiddleware
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


@app.get('/workspace-app', include_in_schema=False)
async def workspace_dashboard():
    if not local_workspace_ui_enabled():
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(_WORKSPACE_UI_DIR / 'index.html')


@app.get('/workspace-app.js', include_in_schema=False)
async def workspace_dashboard_script():
    if not local_workspace_ui_enabled():
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(_WORKSPACE_UI_DIR / 'app.js', media_type='text/javascript')


@app.get("/", include_in_schema=False)
async def dashboard():
    """Serve the dashboard at the backend's own address."""
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
