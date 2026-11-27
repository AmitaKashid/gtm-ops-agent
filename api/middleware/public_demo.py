"""Small, single-instance guardrails for an unauthenticated portfolio demo."""

import asyncio
import os
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class PublicDemoMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.enabled = os.getenv("PUBLIC_DEMO", "").lower() == "true"
        self.requests = deque()
        self.lock = asyncio.Lock()

    async def dispatch(self, request, call_next):
        if not self.enabled:
            return await call_next(request)
        path = request.url.path
        if path == "/hr" or path.startswith("/hr/") or path == "/competitors" or path.startswith("/competitors/"):
            return JSONResponse({"detail": "Unavailable in the public demo."}, status_code=503)
        if request.method == "POST":
            # A conservative process-wide limit; this is not a distributed rate limiter.
            async with self.lock:
                now = time.monotonic()
                while self.requests and self.requests[0] <= now - 3600:
                    self.requests.popleft()
                if len(self.requests) >= 60:
                    return JSONResponse({"detail": "Demo request limit reached. Try again later."}, status_code=429)
                self.requests.append(now)
            length = request.headers.get("content-length")
            if length:
                try:
                    if int(length) > 32768 or int(length) < 0:
                        return JSONResponse({"detail": "Request too large."}, status_code=413)
                except ValueError:
                    return JSONResponse({"detail": "Invalid content length."}, status_code=400)
            # Require a bounded content length for public POST requests.
            else:
                return JSONResponse({"detail": "Content-Length required."}, status_code=411)
        return await call_next(request)
