from typing import Any

from fastapi import APIRouter, Depends, Query

from api.common import current_user_id, invoke_tool, parse_tool_result
from api.schemas.collaboration import (
    TeamMemberRoleRequest,
    TeamOwnerTransferRequest,
    TeamTaskDoneRequest,
    TeamTaskOrderRequest,
    TeamTaskRequest,
)
from tools.team_tools import (
    archive_team,
    create_team_task,
    delete_team_task,
    edit_team_task,
    get_my_teams,
    get_team_detail,
    leave_team,
    remove_team_member,
    reorder_team_tasks,
    transfer_team_owner,
    update_team_member_role,
    update_team_task,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/my")
def mine(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            get_my_teams,
            {"user_id": user_id, "page": page, "page_size": page_size},
        )
    )


@router.get("/{team_id}")
def detail(team_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(invoke_tool(get_team_detail, {"user_id": user_id, "team_id": team_id}), "team")


@router.patch("/{team_id}/tasks/{task_id}")
def update_task(
    team_id: str,
    task_id: str,
    body: TeamTaskDoneRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    if isinstance(body, TeamTaskDoneRequest):
        body = body.model_dump()
    result = parse_tool_result(
        invoke_tool(update_team_task, {"user_id": user_id, "team_id": team_id, "task_id": task_id, "done": bool(body.get("done"))})
    )
    team = result["data"].get("team", {})
    task = next((item for item in team.get("task_list", []) if item.get("id") == task_id), {"id": task_id, "done": bool(body.get("done"))})
    result["data"] = task
    return result


@router.post("/{team_id}/tasks")
def create_task(
    team_id: str,
    body: TeamTaskRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    payload = body.model_dump() if isinstance(body, TeamTaskRequest) else body
    return parse_tool_result(
        invoke_tool(
            create_team_task,
            {
                "user_id": user_id,
                "team_id": team_id,
                "title": payload.get("title", ""),
                "assignee_id": str(payload.get("assignee_id") or ""),
                "due_at": payload.get("due_at", ""),
            },
        ),
        "task",
    )


@router.patch("/{team_id}/tasks/{task_id}/detail")
def edit_task(
    team_id: str,
    task_id: str,
    body: TeamTaskRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    payload = body.model_dump() if isinstance(body, TeamTaskRequest) else body
    return parse_tool_result(
        invoke_tool(
            edit_team_task,
            {
                "user_id": user_id,
                "team_id": team_id,
                "task_id": task_id,
                "title": payload.get("title", ""),
                "assignee_id": str(payload.get("assignee_id") or ""),
                "due_at": payload.get("due_at", ""),
            },
        ),
        "task",
    )


@router.delete("/{team_id}/tasks/{task_id}")
def delete_task(team_id: str, task_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(delete_team_task, {"user_id": user_id, "team_id": team_id, "task_id": task_id})
    )


@router.post("/{team_id}/tasks/reorder")
def reorder_tasks(
    team_id: str,
    body: TeamTaskOrderRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    payload = body.model_dump() if isinstance(body, TeamTaskOrderRequest) else body
    return parse_tool_result(
        invoke_tool(
            reorder_team_tasks,
            {
                "user_id": user_id,
                "team_id": team_id,
                "task_ids": ",".join(payload.get("task_ids") or []),
            },
        )
    )


@router.patch("/{team_id}/members/{target_user_id}/role")
def update_member_role(
    team_id: str,
    target_user_id: str,
    body: TeamMemberRoleRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    payload = body.model_dump() if isinstance(body, TeamMemberRoleRequest) else body
    return parse_tool_result(
        invoke_tool(
            update_team_member_role,
            {
                "user_id": user_id,
                "team_id": team_id,
                "target_user_id": target_user_id,
                "suggested_role": payload.get("suggested_role", ""),
            },
        )
    )


@router.delete("/{team_id}/members/{target_user_id}")
def remove_member(team_id: str, target_user_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            remove_team_member,
            {"user_id": user_id, "team_id": team_id, "target_user_id": target_user_id},
        )
    )


@router.post("/{team_id}/leave")
def leave(team_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(invoke_tool(leave_team, {"user_id": user_id, "team_id": team_id}))


@router.post("/{team_id}/transfer-owner")
def transfer_owner(
    team_id: str,
    body: TeamOwnerTransferRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    payload = body.model_dump() if isinstance(body, TeamOwnerTransferRequest) else body
    return parse_tool_result(
        invoke_tool(
            transfer_team_owner,
            {
                "user_id": user_id,
                "team_id": team_id,
                "target_user_id": str(payload.get("target_user_id") or ""),
            },
        )
    )


@router.post("/{team_id}/archive")
def archive(team_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(invoke_tool(archive_team, {"user_id": user_id, "team_id": team_id}), "team")
