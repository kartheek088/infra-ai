import logging
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("inferago")


async def global_exception_handler(request: Request, exc: Exception):
    """
    Log the full exception server-side, return a sanitized error to the client.
    In development, the error type is included. In production, only a generic
    message is returned.
    """
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    logger.error(
        "Unhandled exception at %s %s: %s\n%s",
        request.method, str(request.url), exc, "".join(tb)
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type":   type(exc).__name__,
            "path":   str(request.url),
        },
    )
