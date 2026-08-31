import json
from typing import Any

from fastapi import APIRouter

from api.common import invoke_tool, parse_tool_result, unwrap_data
from tools.ai_tools import ai_classify_review, ai_match_teammates, ai_post_draft, ai_team_plan
from utils.security import screen_content

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/post-draft")
def post_draft(body: dict[str, Any]) -> dict[str, Any]:
    draft = body.get("draft") or ""
    skills = body.get("user_skills") or ""
    raw = invoke_tool(
        ai_post_draft,
        {
            "message": body.get("message", ""),
            "draft": draft if isinstance(draft, str) else json.dumps(draft, ensure_ascii=False),
            "user_skills": ",".join(skills) if isinstance(skills, list) else str(skills),
        },
    )
    return parse_tool_result(raw)


@router.post("/classify-review")
def classify_review(body: dict[str, Any]) -> dict[str, Any]:
    title = body.get("title") or body.get("activity_name") or ""
    description = body.get("description", "")
    title_screen = screen_content(title)
    description_screen = screen_content(description)
    raw = invoke_tool(
        ai_classify_review,
        {
            "post_title": title_screen.cleaned_text,
            "post_description": description_screen.cleaned_text,
        },
    )
    return parse_tool_result(raw)


@router.post("/match")
def match(body: dict[str, Any]) -> dict[str, Any]:
    raw = invoke_tool(ai_match_teammates, {"post_id": body.get("post_id", "")})
    data = unwrap_data(raw)
    return {"code": 0, "message": data.get("message", "ok"), "data": {"matches": data.get("matches", [])}}


@router.post("/team-plan")
def team_plan(body: dict[str, Any]) -> dict[str, Any]:
    raw = invoke_tool(ai_team_plan, {"team_id": body.get("team_id", "")})
    data = unwrap_data(raw)
    return {"code": 0, "message": data.get("message", "ok"), "data": data.get("team_plan", data)}
