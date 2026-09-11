import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.common import api_ok, current_user_id, invoke_tool, parse_tool_result
from services.content import validate_tag_ids
from services.permissions import can_manage_post
from storage.database.db import get_session
from storage.database.models import AuditLog, Post, PostTag, User
from tools.post_tools import _post_to_dict, create_post, get_my_posts, get_post_detail, list_posts
from utils.security import screen_post_content

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
    kind: str = "",
    topic_id: str = "",
    user_id: str = Depends(current_user_id),
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
                "kind": kind,
                "topic_id": topic_id,
            },
        )
    )


@router.get("/my")
def my_posts(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(get_my_posts, {"user_id": user_id}))
    result["data"] = result["data"]["list"]
    return result


@router.get("/{post_id}")
def post_detail(post_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
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
            "kind": body.get("kind", "casual_invitation"),
            "topic_id": str(body.get("topic_id") or ""),
            "tag_ids": ",".join(body.get("tag_ids") or body.get("tags") or []),
        },
    )
    return parse_tool_result(raw, "post")


@router.patch("/{post_id}")
def update(post_id: int, body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        post = session.get(Post, post_id)
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")

        content_fields = {
            "title",
            "description",
            "main_category",
            "activity_name",
            "target_members",
            "needed_roles",
            "weekly_hours",
            "school_scope",
            "deadline",
            "tag_ids",
        }
        requested_content = content_fields.intersection(body)
        if requested_content and not can_manage_post(session, user, post, "edit_post"):
            raise HTTPException(status_code=403, detail="你没有编辑该帖子的权限")
        if "status" in body and not can_manage_post(session, user, post, "update_status"):
            raise HTTPException(status_code=403, detail="你没有更新该帖子状态的权限")
        if not requested_content and "status" not in body:
            raise HTTPException(status_code=400, detail="没有需要更新的内容")

        changed: dict[str, Any] = {}
        text_limits = {
            "title": 120,
            "description": 5000,
            "main_category": 40,
            "activity_name": 120,
            "weekly_hours": 80,
            "school_scope": 80,
            "deadline": 80,
        }
        for field, limit in text_limits.items():
            if field not in body:
                continue
            value = str(body.get(field) or "").strip()[:limit]
            if field in {"title", "main_category", "activity_name"} and not value:
                raise HTTPException(status_code=400, detail=f"{field} 不能为空")
            setattr(post, field, value or None)
            changed[field] = value
        if "target_members" in body:
            try:
                target_members = int(body.get("target_members"))
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="目标人数不正确") from exc
            if target_members < 1 or target_members > 100:
                raise HTTPException(status_code=400, detail="目标人数应在 1 到 100 之间")
            post.target_members = target_members
            changed["target_members"] = target_members
        if "needed_roles" in body:
            roles = body.get("needed_roles")
            if not isinstance(roles, list):
                raise HTTPException(status_code=400, detail="所需角色格式不正确")
            post.needed_roles = [str(role).strip()[:40] for role in roles if str(role).strip()][:10]
            changed["needed_roles"] = post.needed_roles
        if "tag_ids" in body:
            raw_tag_ids = body.get("tag_ids")
            if not isinstance(raw_tag_ids, list):
                raise HTTPException(status_code=400, detail="标签格式不正确")
            tag_ids = list(dict.fromkeys(str(item).strip() for item in raw_tag_ids if str(item).strip()))[:8]
            invalid = validate_tag_ids(session, tag_ids)
            if invalid:
                raise HTTPException(status_code=400, detail=f"包含未收录的标签：{', '.join(invalid)}")
            session.query(PostTag).filter(PostTag.post_id == post.id).delete()
            session.add_all(PostTag(post_id=post.id, tag_id=tag_id, source="user") for tag_id in tag_ids)
            post.tags = tag_ids
            changed["tag_ids"] = tag_ids
        if "status" in body:
            status = str(body.get("status") or "")
            if status not in {"recruiting", "closed", "full"}:
                raise HTTPException(status_code=400, detail="帖子状态不正确")
            post.status = status
            changed["status"] = status

        screen = screen_post_content(post.title, post.description or "")
        if screen.has_violations:
            raise HTTPException(status_code=400, detail="内容审核未通过")
        post.risk_level = screen.risk_level
        session.add(
            AuditLog(
                user_id=user.id,
                action="post.update",
                target_type="post",
                target_id=str(post.id),
                detail=json.dumps({"fields": sorted(changed)}, ensure_ascii=False),
            )
        )
        session.commit()
        author = session.get(User, post.author_id)
        return api_ok(_post_to_dict(post, author), "帖子已更新")
    finally:
        session.close()
