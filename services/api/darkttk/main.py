from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import models
from .config import get_settings
from .database import Base, engine
from .operations import metrics_response, operations_middleware, readiness, record_operational_error
from .routers import analytics, auth, content, dashboard, intelligence, operations, organizations, providers, tiktok, video, workflow

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.is_production:
        if settings.app_secret.startswith("local-development") or not settings.metrics_token:
            raise RuntimeError("Production requires APP_SECRET and METRICS_TOKEN.")
        if settings.auto_create_schema:
            raise RuntimeError("AUTO_CREATE_SCHEMA must be false in production; run migrations explicitly.")
        if settings.account_delivery_mode.lower() == "mock":
            raise RuntimeError("ACCOUNT_DELIVERY_MODE=mock is forbidden in production.")
    delivery_mode = settings.account_delivery_mode.lower()
    if delivery_mode not in {"disabled", "mock", "resend"}:
        raise RuntimeError("ACCOUNT_DELIVERY_MODE must be disabled, mock, or resend.")
    if delivery_mode == "resend" and not all(
        (settings.resend_api_key, settings.account_email_from, settings.password_recovery_url)
    ):
        raise RuntimeError(
            "Resend delivery requires RESEND_API_KEY, ACCOUNT_EMAIL_FROM, and PASSWORD_RECOVERY_URL."
        )
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    logger.info("api_started", environment=settings.app_env)
    yield
    logger.info("api_stopped")


settings = get_settings()
app = FastAPI(
    title="DarkTTK API",
    version="1.0.0",
    description="API modular para operações de conteúdo com supervisão humana.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


app.middleware("http")(operations_middleware)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, error: Exception):
    logger.exception(
        "unhandled_error", path=request.url.path, error_type=type(error).__name__
    )
    record_operational_error(request, error)
    return JSONResponse(
        status_code=500,
        content={"code": "internal_error", "message": "Ocorreu um erro inesperado."},
    )


@app.get("/health", tags=["Operations"])
async def health():
    return {"status": "ok", "service": "darkttk-api", "version": app.version}


@app.get("/health/live", tags=["Operations"])
async def liveness():
    return {"status": "alive", "service": "darkttk-api", "version": app.version}


@app.get("/health/ready", tags=["Operations"])
async def ready():
    payload, status_code = readiness()
    return JSONResponse(content=payload, status_code=status_code)


@app.get("/metrics", tags=["Operations"], include_in_schema=False)
async def prometheus_metrics(request: Request):
    return metrics_response(request)


app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(dashboard.router)
app.include_router(content.router)
app.include_router(providers.router)
app.include_router(intelligence.router)
app.include_router(video.router)
app.include_router(workflow.router)
app.include_router(tiktok.router)
app.include_router(analytics.router)
app.include_router(operations.router)
