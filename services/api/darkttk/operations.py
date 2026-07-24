from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from hmac import compare_digest

from fastapi import Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select, text

from .config import get_settings
from .database import SessionLocal, engine
from .models import OperationalError


@dataclass
class MetricValue:
    count: int = 0
    total: float = 0


class RuntimeMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, int], MetricValue] = defaultdict(MetricValue)

    def observe(self, method: str, status: int, duration: float) -> None:
        with self._lock:
            value = self._requests[(method, status)]
            value.count += 1
            value.total += duration

    def render(self) -> str:
        lines = [
            "# HELP darkttk_http_requests_total HTTP requests processed.",
            "# TYPE darkttk_http_requests_total counter",
        ]
        with self._lock:
            for (method, status), value in sorted(self._requests.items()):
                labels = f'method="{method}",status="{status}"'
                lines.append(f"darkttk_http_requests_total{{{labels}}} {value.count}")
                lines.append(
                    f"darkttk_http_request_duration_seconds_sum{{{labels}}} {value.total:.6f}"
                )
                lines.append(
                    f"darkttk_http_request_duration_seconds_count{{{labels}}} {value.count}"
                )
        return "\n".join(lines) + "\n"


metrics = RuntimeMetrics()
_local_windows: dict[str, tuple[int, int]] = {}
_local_lock = threading.Lock()
_redis_client = None
_redis_retry_at = 0.0


def _client_ip(request: Request) -> str:
    settings = get_settings()
    peer = request.client.host if request.client else "unknown"
    if settings.trusted_proxy_hops <= 0:
        return peer
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    if len(forwarded) < settings.trusted_proxy_hops:
        return peer
    return forwarded[-settings.trusted_proxy_hops]


def _rate_allowed(key: str, limit: int) -> tuple[bool, int]:
    global _redis_client, _redis_retry_at
    minute = int(time.time() // 60)
    settings = get_settings()
    try:
        import redis

        if _redis_client is None and time.monotonic() >= _redis_retry_at:
            _redis_client = redis.Redis.from_url(
                settings.redis_url, socket_connect_timeout=0.15, socket_timeout=0.15
            )
        if _redis_client is None:
            raise ConnectionError("Redis rate limiter is in cooldown.")
        redis_key = f"darkttk:rate:{minute}:{hashlib.sha256(key.encode()).hexdigest()[:24]}"
        with _redis_client.pipeline() as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, 75)
            count, _ = pipe.execute()
        return int(count) <= limit, 60 - int(time.time() % 60)
    except Exception:
        _redis_client = None
        _redis_retry_at = time.monotonic() + 5
        # Local fallback keeps development and degraded instances protected.
        with _local_lock:
            window, count = _local_windows.get(key, (minute, 0))
            count = count + 1 if window == minute else 1
            _local_windows[key] = (minute, count)
        return count <= limit, 60 - int(time.time() % 60)


async def operations_middleware(request: Request, call_next):
    settings = get_settings()
    started = time.perf_counter()
    request_id = request.headers.get("X-Request-ID") or hashlib.sha256(
        f"{time.time_ns()}:{request.url.path}".encode()
    ).hexdigest()[:24]
    request.state.request_id = request_id

    content_length = request.headers.get("content-length")
    try:
        payload_too_large = bool(content_length and int(content_length) > settings.max_upload_bytes)
    except ValueError:
        payload_too_large = True
    if payload_too_large:
        response = JSONResponse(
            status_code=413,
            content={"code": "payload_too_large", "message": "Corpo da requisição excede o limite."},
        )
    else:
        rate_exempt = request.url.path in {"/health", "/health/live", "/health/ready", "/metrics"}
        limit = (
            settings.auth_rate_limit_per_minute
            if request.url.path.startswith("/v1/auth/")
            else settings.rate_limit_per_minute
        )
        allowed, retry_after = (True, 0) if rate_exempt else _rate_allowed(
            f"{_client_ip(request)}:{request.url.path if limit == settings.auth_rate_limit_per_minute else 'api'}", limit)
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"code": "rate_limited", "message": "Muitas requisições. Tente novamente em instantes."},
                headers={"Retry-After": str(retry_after)},
            )
        else:
            response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "no-store"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    metrics.observe(request.method, response.status_code, time.perf_counter() - started)
    return response


def record_operational_error(request: Request, error: Exception) -> None:
    fingerprint = hashlib.sha256(
        f"{type(error).__name__}:{request.url.path}".encode()
    ).hexdigest()
    try:
        with SessionLocal() as db:
            existing = db.scalar(
                select(OperationalError).where(
                    OperationalError.fingerprint == fingerprint,
                    OperationalError.status == "open",
                )
            )
            if existing:
                existing.occurrences += 1
                existing.last_seen_at = datetime.now(timezone.utc)
            else:
                db.add(
                    OperationalError(
                        service="api",
                        code=type(error).__name__[:100],
                        severity="error",
                        status="open",
                        message_sanitized="Falha interna não tratada.",
                        fingerprint=fingerprint,
                        request_id=getattr(request.state, "request_id", None),
                    )
                )
            db.commit()
    except Exception:
        # Error reporting must never hide the original failure.
        return


def metrics_response(request: Request) -> PlainTextResponse:
    settings = get_settings()
    supplied = request.headers.get("X-Metrics-Token", "")
    if settings.is_production and (
        not settings.metrics_token or not compare_digest(supplied, settings.metrics_token)
    ):
        return PlainTextResponse("not found\n", status_code=404)
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


def readiness() -> tuple[dict[str, object], int]:
    settings = get_settings()
    components: dict[str, str] = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        components["database"] = "ok"
    except Exception:
        components["database"] = "unavailable"

    try:
        import redis

        redis.Redis.from_url(
            settings.redis_url, socket_connect_timeout=0.25, socket_timeout=0.25
        ).ping()
        components["redis"] = "ok"
    except Exception:
        components["redis"] = "unavailable"

    required_ok = components["database"] == "ok" and (
        not settings.readiness_require_redis or components["redis"] == "ok"
    )
    payload = {
        "status": "ready" if required_ok else "not_ready",
        "service": "darkttk-api",
        "version": settings.release_version,
        "components": components,
    }
    return payload, 200 if required_ok else 503
