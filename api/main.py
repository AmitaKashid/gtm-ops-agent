from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
from api.middleware.logging import RequestLoggingMiddleware
from api.routers import crm, leads


app = FastAPI(
    title="GTM Ops Agent",
    description="API for sales and business operations workflows.",
    version="0.1.0",
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(crm.router)
app.include_router(leads.router)


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
