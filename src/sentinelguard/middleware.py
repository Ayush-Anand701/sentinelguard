"""
FastAPI middleware for SentinelGuard.

Add SentinelGuard to any FastAPI app in 3 lines:

    from sentinelguard.middleware import SentinelGuardMiddleware
    app = FastAPI()
    app.add_middleware(SentinelGuardMiddleware)
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sentinelguard import SentinelGuard


class SentinelGuardMiddleware(BaseHTTPMiddleware):
    """
    Middleware that intercepts every incoming request,
    runs it through SentinelGuard, and blocks it if
    the risk score is too high.

    The middleware reads the message from the request body
    and expects a JSON field called "message".
    Session ID is read from the "X-Session-ID" header,
    or falls back to the client's IP address.
    """

    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.guard = SentinelGuard(**kwargs)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only inspect POST requests with JSON body
        if request.method != "POST":
            return await call_next(request)

        try:
            body = await request.json()
            message = body.get("message", "")
        except Exception:
            return await call_next(request)

        if not message:
            return await call_next(request)

        # Get session ID from header or fall back to IP
        session_id = request.headers.get(
            "X-Session-ID",
            request.client.host if request.client else "unknown"
        )

        # Run through SentinelGuard
        decision = self.guard.check(session_id, message)

        # Block if risk is too high
        if decision.action == "block":
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Message blocked by SentinelGuard",
                    "reason": "High risk of prompt injection detected",
                    "risk_score": decision.risk_score,
                    "closest_attack": decision.closest_attack,
                }
            )

        # Allow the request through to your LLM endpoint
        return await call_next(request)