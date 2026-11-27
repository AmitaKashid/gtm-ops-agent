"""Log request outcomes without logging request bodies or query strings."""

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed request_id=%s method=%s path=%s duration_ms=%.1f",
                request_id, request.method, request.url.path,
                (time.monotonic() - started) * 1000,
            )
            raise
        logger.info(
            "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
            request_id, request.method, request.url.path, response.status_code,
            (time.monotonic() - started) * 1000,
        )
        response.headers["X-Request-ID"] = request_id
        return response
