import datetime
import json
from typing import Any

from fastapi import Header, HTTPException

from services.auth_access import ACCESS_DENIED_MESSAGE, auth_email_is_allowed
from services.auth_lifecycle import active_session
from storage.database.db import get_session
from storage.database.models import User
from utils.auth import verify_token


def api_ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data}


def _load_tool_json(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid tool response: {raw}") from exc


def parse_tool_result(raw: str | dict[str, Any], data_key: str | None = None) -> dict[str, Any]:
    payload = _load_tool_json(raw)
    message = payload.get("message") or "ok"

    if payload.get("success") is False or payload.get("sent") is False or payload.get("verified") is False:
        raise HTTPException(status_code=400, detail=message)

    if "list" in payload:
        pagination = payload.get("pagination") if isinstance(payload.get("pagination"), dict) else {}
        total = int(pagination.get("total", payload.get("total", len(payload.get("list", [])))))
        page = int(pagination.get("page", payload.get("page", 1)))
        page_size = int(
            pagination.get("page_size", payload.get("page_size", len(payload.get("list", []))))
        )
        return api_ok(
            {
                "list": payload.get("list", []),
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": int(pagination.get("pages", (total + page_size - 1) // page_size if page_size else 0)),
            },
            message,
        )

    if data_key and data_key in payload:
        return api_ok(payload[data_key], message)

    data = {k: v for k, v in payload.items() if k not in {"success", "message"}}
    return api_ok(data, message)


def unwrap_data(raw: str | dict[str, Any], data_key: str | None = None) -> Any:
    return parse_tool_result(raw, data_key)["data"]


def current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload or not payload.get("user_id") or not payload.get("jti"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    session = get_session()
    try:
        user_id = int(payload["user_id"])
        user = session.get(User, user_id)
        if user is None or user.account_status != "active":
            raise HTTPException(status_code=401, detail="Account is inactive")
        account_email = user.email or user.verified_email or ""
        if not auth_email_is_allowed(account_email):
            raise HTTPException(status_code=403, detail=ACCESS_DENIED_MESSAGE)
        auth_session = active_session(session, str(payload["jti"]), user_id)
        if auth_session is None:
            raise HTTPException(status_code=401, detail="Invalid or revoked token")
        now = datetime.datetime.now(datetime.timezone.utc)
        last_seen = auth_session.last_seen_at
        if last_seen is None or (
            now - (last_seen if last_seen.tzinfo else last_seen.replace(tzinfo=datetime.timezone.utc))
        ).total_seconds() >= 300:
            auth_session.last_seen_at = now
            session.commit()
        return str(user_id)
    finally:
        session.close()


def invoke_tool(tool: Any, payload: dict[str, Any]) -> str:
    return tool.invoke(payload)
