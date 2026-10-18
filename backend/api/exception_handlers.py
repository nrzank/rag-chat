import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.base.exceptions import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "%s: %s",
        exc.code,
        exc.message,
        extra={"code": exc.code, "path": request.url.path, "context": exc.context},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "params": exc.params},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's default 422 body breaks the {code, message, params} contract and echoes
    the submitted value back. Report the failing fields instead."""
    fields = [".".join(str(part) for part in error["loc"][1:]) for error in exc.errors()]
    logger.warning("validation failed at %s: %s", request.url.path, fields)
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "Request validation failed",
            "params": {"fields": fields},
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error at %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "internal_error", "message": "Internal server error", "params": {}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
