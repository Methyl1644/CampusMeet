from typing import Any

from fastapi import APIRouter, Depends, Query

from api.common import current_user_id, invoke_tool, parse_tool_result
from api.schemas.collaboration import ApplicationCreateRequest
from tools.application_tools import (
    accept_application,
    create_application,
    get_applications,
    get_my_applications,
    reject_application,
    withdraw_application,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("")
def create(body: ApplicationCreateRequest, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    if isinstance(body, ApplicationCreateRequest):
        body = body.model_dump()
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
def list_received(
    post_id: str = "",
    user_id: str = Depends(current_user_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    page = page if isinstance(page, int) else 1
    page_size = page_size if isinstance(page_size, int) else 20
    return parse_tool_result(
        invoke_tool(
            get_applications,
            {"user_id": user_id, "post_id": post_id, "page": page, "page_size": page_size},
        )
    )


@router.get("/my")
def mine(
    user_id: str = Depends(current_user_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    page = page if isinstance(page, int) else 1
    page_size = page_size if isinstance(page_size, int) else 20
    return parse_tool_result(
        invoke_tool(
            get_my_applications,
            {"user_id": user_id, "page": page, "page_size": page_size},
        )
    )


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


@router.post("/{application_id}/withdraw")
def withdraw(application_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(
        invoke_tool(withdraw_application, {"user_id": user_id, "application_id": application_id}),
        "application",
    )
    result["data"] = {"withdrawn": True, **result["data"]}
    return result
