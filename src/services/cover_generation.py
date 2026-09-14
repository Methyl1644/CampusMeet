import json
import logging
import os
from typing import Any, Iterable
from urllib.parse import urlparse

from services.observability import record_metric


logger = logging.getLogger(__name__)
COVER_TIMEOUT_SECONDS = 45
MAX_COVER_URL_LENGTH = 4096
_URL_KEYS = ("image_url", "imageUrl", "cover_url", "coverUrl", "output_url", "file_url", "url")
_WRAPPER_KEYS = ("data", "output", "result", "image", "images")
_SUCCESS_STATUSES = {"success", "succeeded", "completed", "complete", "ok"}
_FAILURE_STATUSES = {"failed", "failure", "error", "cancelled", "canceled"}


def _valid_public_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_COVER_URL_LENGTH:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return None
    return candidate


def _extract_image_url(value: Any, depth: int = 0) -> str | None:
    if depth > 6:
        return None
    direct = _valid_public_url(value)
    if direct:
        return direct
    if isinstance(value, str):
        try:
            return _extract_image_url(json.loads(value), depth + 1)
        except (json.JSONDecodeError, TypeError):
            return None
    if isinstance(value, list):
        for item in value:
            if found := _extract_image_url(item, depth + 1):
                return found
        return None
    if not isinstance(value, dict):
        return None
    for key in _URL_KEYS:
        if found := _extract_image_url(value.get(key), depth + 1):
            return found
    for key in _WRAPPER_KEYS:
        if found := _extract_image_url(value.get(key), depth + 1):
            return found
    return None


def _extract_status(value: Any, depth: int = 0) -> str | None:
    if depth > 6:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _SUCCESS_STATUSES | _FAILURE_STATUSES:
            return normalized
        try:
            return _extract_status(json.loads(value), depth + 1)
        except (json.JSONDecodeError, TypeError):
            return None
    if isinstance(value, list):
        for item in value:
            if status := _extract_status(item, depth + 1):
                return status
        return None
    if not isinstance(value, dict):
        return None
    if status := _extract_status(value.get("status"), depth + 1):
        return status
    for key in _WRAPPER_KEYS:
        if status := _extract_status(value.get(key), depth + 1):
            return status
    return None


def generate_content_cover(
    *,
    content_type: str,
    title: str,
    description: str = "",
    category: str = "",
    location: str = "",
    roles: Iterable[str] = (),
) -> str | None:
    api_url = os.getenv("COZE_COVER_API_URL", "").strip()
    token = os.getenv("COZE_COVER_API_TOKEN", "").strip()
    if not api_url or not token:
        record_metric("coze.calls", workflow="COZE_COVER_API_URL", result="not_configured")
        return None
    parsed = urlparse(api_url)
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not hostname.endswith(".coze.site")
        or parsed.path.rstrip("/") != "/run"
        or parsed.username
        or parsed.password
    ):
        logger.warning("Rejected invalid Coze cover deployment URL")
        record_metric("coze.calls", workflow="COZE_COVER_API_URL", result="invalid_url")
        return None

    payload = {
        "content_type": str(content_type or "").strip()[:40],
        "title": str(title or "").strip()[:120],
        "description": str(description or "").strip()[:3000],
        "category": str(category or "").strip()[:120],
        "location": str(location or "").strip()[:200],
        "roles": "、".join(str(role).strip() for role in roles if str(role).strip())[:500],
    }
    try:
        import requests

        response = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=COVER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        if isinstance(body, dict) and body.get("code") not in (None, 0, "0"):
            record_metric("coze.calls", workflow="COZE_COVER_API_URL", result="provider_error")
            return None
        status = _extract_status(body)
        if status in _FAILURE_STATUSES:
            record_metric("coze.calls", workflow="COZE_COVER_API_URL", result="provider_failed")
            return None
        cover_url = _extract_image_url(body)
        record_metric(
            "coze.calls",
            workflow="COZE_COVER_API_URL",
            result="success" if cover_url else "invalid_output",
        )
        return cover_url
    except Exception as exc:
        logger.warning("Coze cover generation failed: %s", exc)
        record_metric("coze.calls", workflow="COZE_COVER_API_URL", result="timeout_or_error")
        return None
