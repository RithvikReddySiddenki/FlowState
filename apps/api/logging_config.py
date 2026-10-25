"""Request logs omit query strings, headers, bodies and exception parameters."""

import json
import logging
import time
from uuid import UUID, uuid4

from fastapi import Request

from apps.api.metrics import observe

logger = logging.getLogger("flowstate")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
logging.getLogger("httpx").setLevel(logging.WARNING)


async def request_logging(request: Request, call_next):
    try:
        request_id = str(UUID(request.headers.get("x-request-id", "")))
    except ValueError:
        request_id = str(uuid4())
    started = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        route = request.scope.get("route")
        route_name = getattr(route, "path", "unmatched")
        elapsed = time.monotonic() - started
        observe(request.method, route_name, status, elapsed)
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route_name,
                    "status": status,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                }
            )
        )
