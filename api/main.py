from dotenv import load_dotenv
import os

load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from api.middleware.logging import RequestLoggingMiddleware
from api.routers import crm, leads, emails, meetings, competitors, hr_onboarding


app = FastAPI(
    title="GTM Ops Agent",
    description="API for sales and business operations workflows.",
    version="0.1.0",
)

def allowed_origins() -> list[str]:
    """Return explicit browser origins from configuration."""
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8080,http://localhost:8080")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(crm.router)
app.include_router(leads.router)
app.include_router(emails.router)
app.include_router(meetings.router)
app.include_router(competitors.router)
app.include_router(hr_onboarding.router)


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
