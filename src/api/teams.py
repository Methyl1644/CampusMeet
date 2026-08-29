from typing import Any

from fastapi import APIRouter, Depends

from api.common import current_user_id, invoke_tool, parse_tool_result
from tools.team_tools import get_my_teams, get_team_detail, update_team_task

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/my")
def mine(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(get_my_teams, {"user_id": user_id}))
    result["data"] = result["data"]["list"]
    return result


@router.get("/{team_id}")
def detail(team_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(invoke_tool(get_team_detail, {"user_id": user_id, "team_id": team_id}), "team")


@router.patch("/{team_id}/tasks/{task_id}")
def update_task(team_id: str, task_id: str, body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(
        invoke_tool(update_team_task, {"user_id": user_id, "team_id": team_id, "task_id": task_id, "done": bool(body.get("done"))})
    )
    team = result["data"].get("team", {})
    task = next((item for item in team.get("task_list", []) if item.get("id") == task_id), {"id": task_id, "done": bool(body.get("done"))})
    result["data"] = task
    return result
