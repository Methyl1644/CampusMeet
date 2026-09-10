from typing import Any

from fastapi import APIRouter, Depends

from api.common import current_user_id, invoke_tool, parse_tool_result, unwrap_data
from tools.auth_tools import (
    get_user_profile,
    login_user,
    register_auth_send_code,
    register_user,
    update_user_profile,
    verify_campus_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-code")
def send_code(body: dict[str, Any]) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            register_auth_send_code,
            {
                "account": body.get("account", ""),
                "purpose": body.get("purpose", "register"),
            },
        )
    )


@router.post("/register")
def register(body: dict[str, Any]) -> dict[str, Any]:
    skills = body.get("skills") or []
    raw = invoke_tool(
        register_user,
        {
            "account": body.get("account", ""),
            "code": body.get("code", ""),
            "password": body.get("password", ""),
            "nickname": body.get("nickname", ""),
            "major": body.get("major", ""),
            "grade": body.get("grade", ""),
            "skills": ",".join(skills) if isinstance(skills, list) else str(skills),
            "wechat": body.get("wechat", ""),
        },
    )
    data = unwrap_data(raw)
    return {"code": 0, "message": data.get("message", "ok"), "data": {"token": data["token"], "user": data["user"]}}


@router.post("/login")
def login(body: dict[str, Any]) -> dict[str, Any]:
    raw = invoke_tool(
        login_user,
        {
            "account": body.get("account", ""),
            "password": body.get("password", ""),
            "code": body.get("code", ""),
        },
    )
    data = unwrap_data(raw)
    return {"code": 0, "message": "ok", "data": {"token": data["token"], "user": data["user"]}}


@router.post("/verify-email")
def verify_email(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            verify_campus_email,
            {"user_id": user_id, "email": body.get("email", ""), "code": body.get("code", "")},
        )
    )


@router.get("/profile")
def profile(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(invoke_tool(get_user_profile, {"user_id": user_id}), "user")


@router.patch("/profile")
def update_profile(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    skills = body.get("skills") or ""
    raw = invoke_tool(
        update_user_profile,
        {
            "user_id": user_id,
            "nickname": body.get("nickname", ""),
            "major": body.get("major", ""),
            "grade": body.get("grade", ""),
            "skills": ",".join(skills) if isinstance(skills, list) else str(skills),
            "wechat": body.get("wechat", ""),
        },
    )
    return parse_tool_result(raw, "user")
