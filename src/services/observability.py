from __future__ import annotations

import contextvars
import json
import logging
import re
import threading
import time
import uuid
from collections import Counter
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


logger = logging.getLogger("campusmate.http")
request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
_metrics_lock = threading.Lock()
_metrics: Counter = Counter()

_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "current_password",
    "new_password",
    "token",
    "api_token",
    "api_key",
    "secret",
    "verification_code",
    "code",
    "evidence",
    "evidence_reference",
    "message",
    "content",
    "phone",
    "wechat",
    "email",
}
_EMAIL_RE = re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_WECHAT_RE = re.compile(r"(?i)(?:微信|wechat)\s*[:：]?\s*[A-Za-z][\w.-]{3,}")
_SAFE_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def redact_sensitive(value: Any, *, key: str = "") -> Any:
    if key.casefold() in _SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): redact_sensitive(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
        redacted = _PHONE_RE.sub("[REDACTED_PHONE]", redacted)
        return _WECHAT_RE.sub("[REDACTED_CONTACT]", redacted)
    return value


def record_metric(name: str, amount: int = 1, **labels: str) -> None:
    suffix = ",".join(f"{key}={labels[key]}" for key in sorted(labels))
    metric_key = f"{name}|{suffix}" if suffix else name
    with _metrics_lock:
        _metrics[metric_key] += amount


def metrics_snapshot() -> dict[str, int]:
    with _metrics_lock:
        return dict(_metrics)


def _error_response(request: Request, status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "message": message,
            "data": None,
            "request_id": getattr(request.state, "request_id", ""),
        },
    )


def install_observability(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        message = detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)
        return _error_response(request, exc.status_code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        record_metric("http.validation_error", path=request.url.path)
        return _error_response(request, 422, "请求参数不正确")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        record_metric("http.unhandled_error", path=request.url.path)
        logger.exception(
            json.dumps(
                {
                    "event": "http.unhandled_error",
                    "request_id": getattr(request.state, "request_id", ""),
                    "method": request.method,
                    "path": request.url.path,
                    "exception_type": type(exc).__name__,
                },
                ensure_ascii=True,
            )
        )
        return _error_response(request, 500, "服务器暂时无法处理该请求")

    @app.middleware("http")
    async def request_observability(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _SAFE_REQUEST_ID_RE.fullmatch(supplied) else uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                # Return inside the CORS middleware so browsers can read 500 responses.
                response = await unhandled_exception_handler(request, exc)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            record_metric("http.requests", method=request.method, status=str(status_code))
            record_metric("http.duration_ms_total", int(duration_ms), method=request.method)
            logger.info(
                json.dumps(
                    {
                        "event": "http.request",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": duration_ms,
                    },
                    ensure_ascii=True,
                )
            )
            request_id_context.reset(token)
