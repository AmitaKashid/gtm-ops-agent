"""Keep legacy unauthenticated demo routes out of a hosted workspace service."""
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class HostedWorkspaceBoundary(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        enabled = (os.getenv('APP_ENV', '').lower() != 'development'
                   and os.getenv('WORKSPACE_HOSTED_UI_ENABLED', '').lower() == 'true'
                   and os.getenv('WORKSPACE_ENABLED', '').lower() == 'true'
                   and os.getenv('PUBLIC_DEMO', '').lower() != 'true')
        path = request.url.path
        if enabled and path not in {'/', '/health', '/workspace-app', '/workspace-app.js', '/workspace-config'} and not path.startswith('/workspace/'):
            return JSONResponse({'detail': 'Not available on this workspace service.'}, status_code=404)
        return await call_next(request)
