from typing import Any

from fastapi import APIRouter, Depends

from api.common import current_user_id, invoke_tool, parse_tool_result
from tools.post_tools import create_post, get_my_posts, get_post_detail, list_posts

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("")
def posts(
    tab: str = "recommend",
    page: int = 1,
    page_size: int = 10,
    category: str = "",
    tags: str = "",
    keyword: str = "",
    sort: str = "latest",
) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            list_posts,
            {
                "tab": tab,
                "page": page,
                "page_size": page_size,
                "category": category,
                "tags": tags,
                "keyword": keyword,
                "sort": sort,
            },
        )
    )


@router.get("/my")
def my_posts(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(get_my_posts, {"user_id": user_id}))
    result["data"] = result["data"]["list"]
    return result


@router.get("/{post_id}")
def post_detail(post_id: str) -> dict[str, Any]:
    return parse_tool_result(invoke_tool(get_post_detail, {"post_id": post_id}), "post")


@router.post("")
def create(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    needed_roles = body.get("needed_roles") or []
    raw = invoke_tool(
        create_post,
        {
            "user_id": user_id,
            "title": body.get("title") or body.get("activity_name") or "Team post",
            "description": body.get("description", ""),
            "main_category": body.get("main_category") or "校园生活",
            "activity_name": body.get("activity_name") or body.get("title") or "Untitled activity",
            "target_members": int(body.get("target_members") or 1),
            "needed_roles": ",".join(needed_roles) if isinstance(needed_roles, list) else str(needed_roles),
            "weekly_hours": body.get("weekly_hours", ""),
            "school_scope": body.get("school_scope", ""),
            "deadline": body.get("deadline", ""),
        },
    )
    return parse_tool_result(raw, "post")
