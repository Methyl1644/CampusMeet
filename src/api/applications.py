from typing import Any

from fastapi import APIRouter, Depends

from api.common import current_user_id, invoke_tool, parse_tool_result
from tools.application_tools import (
    accept_application,
    create_application,
    get_applications,
    get_my_applications,
    reject_application,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("")
def create(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    questions = body.get("questions") or []
    return parse_tool_result(
        invoke_tool(
            create_application,
            {
                "user_id": user_id,
                "post_id": body.get("post_id", ""),
                "role_wanted": body.get("role_wanted", ""),
                "experience": body.get("experience", ""),
                "available_time": body.get("available_time", ""),
                "reason": body.get("reason", ""),
                "questions": ",".join(questions) if isinstance(questions, list) else str(questions),
            },
        ),
        "application",
    )


@router.get("")
def list_received(post_id: str = "", user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(get_applications, {"user_id": user_id, "post_id": post_id}))
    result["data"] = result["data"]["list"]
    return result


@router.get("/my")
def mine(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(get_my_applications, {"user_id": user_id}))
    result["data"] = result["data"]["list"]
    return result


@router.post("/{application_id}/accept")
def accept(application_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(accept_application, {"user_id": user_id, "application_id": application_id}))
    result["data"] = {"accepted": True, **result["data"]}
    return result


@router.post("/{application_id}/reject")
def reject(application_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(reject_application, {"user_id": user_id, "application_id": application_id}))
    result["data"] = {"rejected": True, **result["data"]}
    return result
