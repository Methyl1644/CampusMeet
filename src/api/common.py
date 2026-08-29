import json
from typing import Any

from fastapi import Header, HTTPException

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
        return api_ok(
            {
                "list": payload.get("list", []),
                "total": payload.get("total", len(payload.get("list", []))),
                "page": payload.get("page", 1),
                "page_size": payload.get("page_size", len(payload.get("list", []))),
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
    if not payload or not payload.get("user_id"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return str(payload["user_id"])


def invoke_tool(tool: Any, payload: dict[str, Any]) -> str:
    return tool.invoke(payload)
