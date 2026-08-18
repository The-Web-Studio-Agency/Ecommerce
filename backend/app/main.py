from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_router
from app.core.cache import close_redis, redis_healthy
from app.core.config import get_settings
from app.core.database import dispose_engine, engine
from app.core.exceptions import AppError, RateLimitedError
from app.core.logging import configure_logging, get_logger, set_request_id
from app.core.request_context import sanitize_request_id
from app.core.responses import ErrorPayload, ErrorResponse

settings = get_settings()
logger = get_logger("api")

API_DESCRIPTION = """
Multi-tenant e-commerce SaaS platform API.

**Tenancy.** The tenant comes from the hostname the request arrived on, which
the caller cannot choose. A request to an unregistered domain is a 404; a token
issued by one storefront cannot authenticate against another.

**Authentication.** Customers sign in with a phone number and a one-time code.
Admins sign in with a password. Staff verify a password first and then a
one-time code. All successful logins end in a JWT access token plus a rotating
refresh token.

**Responses.** Every endpoint returns `{success, message, data}`;
every error returns `{success, message, error:{code, details, request_id}}`.
"""

TAGS_METADATA = [
    {"name": "Health", "description": "Liveness and readiness probes."},
    {"name": "Auth", "description": "Customer authentication (phone + one-time code)."},
    {"name": "Admin Auth", "description": "Admin and staff authentication."},
    {"name": "Catalogue", "description": "Categories, products and product variants."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("api.startup environment=%s", settings.environment)
    yield
    await dispose_engine()
    await close_redis()
    logger.info("api.shutdown")


def _error_response(
    *,
    status_code: int,
    message: str,
    code: str,
    details: list[dict] | None = None,
    request_id: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        message=message,
        error=ErrorPayload(code=code, details=details or [], request_id=request_id),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )


def create_app() -> FastAPI:
    configure_logging()
    docs = settings.api_docs_enabled
    app = FastAPI(
        title=settings.app_name,
        description=API_DESCRIPTION,
        version="1.0.0",
        openapi_tags=TAGS_METADATA,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next: Callable[[Request], Awaitable]):
        request_id = sanitize_request_id(request.headers.get("X-Request-Id"))
        set_request_id(request_id)
        request.state.request_id = request_id

        started = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - started) * 1000

        response.headers["X-Request-Id"] = request_id
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        if exc.status_code >= 500:
            logger.error("app_error %s: %s", exc.error_code, exc.message)
        else:
            logger.info("app_error %s: %s", exc.error_code, exc.message)

        headers = None
        if isinstance(exc, RateLimitedError) and exc.retry_after_seconds is not None:
            headers = {"Retry-After": str(exc.retry_after_seconds)}

        return _error_response(
            status_code=exc.status_code,
            message=exc.message,
            code=exc.error_code,
            details=exc.details,
            request_id=request_id,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", [])[1:]) or "body",
                "issue": error.get("msg", "invalid"),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return _error_response(
            status_code=422,
            message="Request validation failed",
            code="VALIDATION_ERROR",
            details=details,
            request_id=getattr(request.state, "request_id", None),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        codes = {
            status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_FAILED",
            status.HTTP_403_FORBIDDEN: "PERMISSION_DENIED",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        }
        return _error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            code=codes.get(exc.status_code, "HTTP_ERROR"),
            request_id=getattr(request.state, "request_id", None),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.error("db.integrity_error %s", exc.orig, exc_info=False)
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            message="The request conflicts with existing data",
            code="CONFLICT",
            request_id=getattr(request.state, "request_id", None),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("db.error %s", type(exc).__name__)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="A database error occurred",
            code="DATABASE_ERROR",
            request_id=getattr(request.state, "request_id", None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error %s", type(exc).__name__)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred",
            code="INTERNAL_ERROR",
            request_id=getattr(request.state, "request_id", None),
        )


    @app.get("/health/live", tags=["Health"], summary="Liveness probe")
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"], summary="Readiness probe")
    async def readiness() -> JSONResponse:
        database_ok = True
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            logger.error("health.database_unavailable %s", exc)
            database_ok = False

        cache_ok = await redis_healthy()
        if not cache_ok:
            logger.warning("health.redis_degraded rate limiting is not being enforced")

        pool = engine.pool
        return JSONResponse(
            status_code=status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "ready" if database_ok else "unavailable",
                "checks": {
                    "database": "ok" if database_ok else "unavailable",
                    "redis": "ok" if cache_ok else "degraded",
                },
                "pool": {
                    "size": pool.size(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                },
            },
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
