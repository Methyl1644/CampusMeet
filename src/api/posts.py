import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from api.agent import classify_review, store_tag_proposals
from api.common import api_ok, current_user_id, invoke_tool, parse_tool_result
from api.schemas.collaboration import PostCreateRequest, PostUpdateRequest
from services.content import validate_tag_ids
from services.publish_context import publish_context, missing_fields, inherited_tag_ids, merge_tag_ids
from services.content_moderation import ModerationContext, moderate_content
from services.cover_generation import generate_content_cover
from services.deadlines import parse_deadline_at
from services.moderation_cases import has_active_restriction
from services.collaboration_lifecycle import PUBLIC_POST_STATUSES, transition_post
from services.explore import project_group_cards
from services.permissions import can_manage_post
from services.participation import (
    ParticipationError,
    commit_post_participation,
    join_post_directly,
    validate_post_participation,
)
from storage.database.db import get_session
from storage.database.models import AuditLog, Post, PostTag, User
from services.uploads import attach_new_post_cover
from tools.post_tools import _post_to_dict, create_post, get_my_posts, get_post_detail, list_posts
from utils.security import screen_post_content

router = APIRouter(prefix="/posts", tags=["posts"])
logger = logging.getLogger(__name__)
MAIN_CATEGORIES = {"竞赛与项目", "学习与科研", "体育与健身", "旅行与户外", "校园生活", "拼团与AA"}
RISK_LEVELS = {"low": 0, "medium": 1, "high": 2}


def _participation_http_error(exc: ParticipationError) -> HTTPException:
    status_code = 403 if exc.code == "participation.official_signup_forbidden" else 409
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _classification_review(title: str, description: str, user_id: str) -> dict[str, Any]:
    try:
        result = classify_review(
            {
                "title": title,
                "description": description,
                "persist_tag_proposals": False,
            },
            user_id,
        )
    except HTTPException as exc:
        if exc.status_code < 500:
            raise
        logger.warning("AI classification unavailable; using local review: %s", exc.detail)
        return {}
    except Exception as exc:
        logger.warning("AI classification failed; using local review: %s", exc)
        return {}

    review = result.get("data") if isinstance(result, dict) and isinstance(result.get("data"), dict) else {}
    risk_level = str(review.get("risk_level") or "low").strip().lower()
    review["risk_level"] = risk_level if risk_level in RISK_LEVELS else "medium"
    if review.get("main_category") not in MAIN_CATEGORIES:
        review["main_category"] = None
    return review


def _moderate_post(body: dict[str, Any], user_id: str, *, title: str, description: str) -> None:
    decision = moderate_content(
        title,
        ModerationContext(
            surface="post",
            user_id=user_id,
            structured_fields={
                "description": description,
                "activity_name": body.get("activity_name"),
                "needed_roles": body.get("needed_roles"),
                "weekly_hours": body.get("weekly_hours"),
                "school_scope": body.get("school_scope"),
                "deadline": body.get("deadline"),
            },
        ),
    )
    if decision.action != "allow":
        logger.info(
            "Post moderation rejected user=%s action=%s rules=%s",
            user_id,
            decision.action,
            decision.rule_ids,
        )
        detail = f"内容存在风险，{decision.user_message}"
        if decision.suggestions:
            detail = f"{detail}：{'；'.join(decision.suggestions)}"
        raise HTTPException(status_code=400, detail=detail)


@router.get("")
def posts(
    tab: str = "recommend",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=40),
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
                "user_id": user_id,
            },
        )
    )


@router.get("/my")
def my_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            get_my_posts,
            {"user_id": user_id, "page": page, "page_size": page_size},
        )
    )


@router.get("/{post_id}")
def post_detail(post_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(get_post_detail, {"post_id": post_id, "user_id": user_id}),
        "post",
    )


@router.post("")
def create(body: PostCreateRequest, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    if isinstance(body, PostCreateRequest):
        body = body.model_dump(exclude_none=True)
    if body.get("client_request_id"):
        with get_session() as session:
            existing = session.scalar(select(Post).where(Post.author_id == int(user_id), Post.client_request_id == body["client_request_id"]))
            if existing:
                return api_ok(_post_to_dict(existing, session.get(User, int(user_id)), session, viewer_id=int(user_id)))
    if body.get("publish_context_revision"):
        with get_session() as session:
            context = publish_context(session, session.get(User, int(user_id)), body.get("kind", "casual_invitation"), str(body.get("topic_id") or ""))
            if context["revision"] != body["publish_context_revision"]:
                raise HTTPException(409, "活动发布规则已更新，请重新加载后核对")
            if body.get("purpose", "team_recruitment") not in context["allowed_purposes"]:
                raise HTTPException(403, "当前用途不可发布")
            if context["activity"]:
                body["activity_name"] = context["activity"]["title"]
            missing = missing_fields(body, {"needed_roles": {"status": "none"}}, context["kind"], body.get("purpose", "team_recruitment"))
            if body.get("purpose") == "official_signup" and body.get("target_members", 0) > context["max_members"]:
                missing.append("target_members")
            if missing:
                raise HTTPException(400, "请补全发布资料：" + ", ".join(missing))
    title = body.get("title") or body.get("activity_name") or "Team post"
    description = body.get("description", "")
    _moderate_post(body, user_id, title=title, description=description)
    local_screen = screen_post_content(title, description)
    if local_screen.has_violations:
        raise HTTPException(status_code=400, detail="内容审核未通过")
    if local_screen.risk_level == "high":
        raise HTTPException(status_code=400, detail="内容风险过高，请修改后再发布")

    review = _classification_review(title, description, user_id)
    review_risk_level = str(review.get("risk_level") or "low")
    resolved_risk_level = max(
        (local_screen.risk_level, review_risk_level),
        key=lambda value: RISK_LEVELS[value],
    )
    if resolved_risk_level == "high":
        raise HTTPException(status_code=400, detail="内容风险过高，请根据审核建议修改后再发布")

    selected_tag_ids = body.get("tag_ids") or body.get("tags") or []
    if not isinstance(selected_tag_ids, list):
        selected_tag_ids = []
    selected_tag_ids = list(dict.fromkeys(str(tag_id) for tag_id in selected_tag_ids if str(tag_id)))[:8]
    suggested_tag_ids = review.get("tag_ids") if isinstance(review.get("tag_ids"), list) else []
    suggested_tag_ids = [
        str(tag_id)
        for tag_id in suggested_tag_ids
        if str(tag_id) and str(tag_id) not in selected_tag_ids
    ]
    needed_roles = body.get("needed_roles") or []
    resolved_category = body.get("main_category") or review.get("main_category") or "校园生活"
    generated_cover_url = None
    if not body.get("cover_upload_id"):
        generated_cover_url = generate_content_cover(
            content_type="post",
            title=title,
            description=description,
            category=resolved_category,
            location=body.get("school_scope", ""),
            roles=needed_roles if isinstance(needed_roles, list) else [str(needed_roles)],
        )
    raw = invoke_tool(
        create_post,
        {
            "user_id": user_id,
            "title": title,
            "description": description,
            "main_category": resolved_category,
            "activity_name": body.get("activity_name") or body.get("title") or "Untitled activity",
            "target_members": int(body.get("target_members") or 1),
            "needed_roles": ",".join(needed_roles) if isinstance(needed_roles, list) else str(needed_roles),
            "weekly_hours": body.get("weekly_hours", ""),
            "school_scope": body.get("school_scope", ""),
            "deadline": body.get("deadline", ""),
            "kind": body.get("kind", "casual_invitation"),
            "topic_id": str(body.get("topic_id") or ""),
            "tag_ids": ",".join(selected_tag_ids),
            "suggested_tag_ids": ",".join(dict.fromkeys(suggested_tag_ids)),
            "review_risk_level": resolved_risk_level,
            "purpose": body.get("purpose", "team_recruitment"),
            "join_mode": body.get("join_mode") or "",
            "client_request_id": body.get("client_request_id") or "",
            "cover_upload_id": body.get("cover_upload_id") or "",
            "generated_cover_url": generated_cover_url or "",
        },
    )
    raw_payload = json.loads(raw) if isinstance(raw, str) else raw
    if raw_payload.get("success") is False and raw_payload.get("error_code"):
        code = str(raw_payload["error_code"])
        if code.startswith("participation."):
            raise _participation_http_error(ParticipationError(code))
    result = parse_tool_result(raw, "post")
    concepts = review.get("unknown_concepts") if isinstance(review.get("unknown_concepts"), list) else []
    if concepts:
        try:
            proposal_refs = store_tag_proposals(user_id, title, description, concepts)
            if isinstance(result.get("data"), dict):
                result["data"]["tag_proposals"] = proposal_refs
        except Exception as exc:
            logger.warning("Post created but tag proposals could not be stored: %s", exc)
    return result


@router.patch("/{post_id}")
def update(post_id: int, body: PostUpdateRequest, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    if isinstance(body, PostUpdateRequest):
        body = body.model_dump(exclude_unset=True)
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        if has_active_restriction(session, user.id, "posting"):
            raise HTTPException(status_code=403, detail="当前账号处于发布限制期")
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
            "purpose",
            "join_mode",
            "cover_upload_id",
        }
        requested_content = content_fields.intersection(body)
        if requested_content and not can_manage_post(session, user, post, "edit_post"):
            raise HTTPException(status_code=403, detail="你没有编辑该帖子的权限")
        if not requested_content:
            raise HTTPException(status_code=400, detail="没有需要更新的内容")

        try:
            participation = validate_post_participation(session, user, body, existing=post)
        except ParticipationError as exc:
            raise _participation_http_error(exc) from exc

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
            if field == "deadline":
                post.deadline_at = parse_deadline_at(value)
            changed[field] = value
        if "target_members" in body:
            try:
                target_members = int(body.get("target_members"))
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="目标人数不正确") from exc
            limit = 10000 if participation.purpose == "official_signup" else 100
            if target_members < 1 or target_members > limit:
                raise HTTPException(status_code=400, detail=f"目标人数应在 1 到 {limit} 之间")
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
            try:
                tag_ids = merge_tag_ids(inherited_tag_ids(session, post.topic_id), [str(item).strip() for item in raw_tag_ids if str(item).strip()])
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
            invalid = validate_tag_ids(session, tag_ids)
            if invalid:
                raise HTTPException(status_code=400, detail=f"包含未收录的标签：{', '.join(invalid)}")
            session.query(PostTag).filter(PostTag.post_id == post.id).delete()
            session.add_all(PostTag(post_id=post.id, tag_id=tag_id, source="user") for tag_id in tag_ids)
            post.tags = tag_ids
            changed["tag_ids"] = tag_ids
        if "purpose" in body or "join_mode" in body:
            post.purpose = participation.purpose
            post.join_mode = participation.join_mode
            if "purpose" in body:
                changed["purpose"] = str(participation.purpose)
            if "join_mode" in body:
                changed["join_mode"] = str(participation.join_mode)
        if body.get("cover_upload_id"):
            try:
                attach_new_post_cover(session, user, post, str(body["cover_upload_id"]))
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            changed["cover_upload_id"] = str(body["cover_upload_id"])
        _moderate_post(
            {
                "activity_name": post.activity_name,
                "needed_roles": post.needed_roles,
                "weekly_hours": post.weekly_hours,
                "school_scope": post.school_scope,
                "deadline": post.deadline,
            },
            user_id,
            title=post.title,
            description=post.description or "",
        )
        screen = screen_post_content(post.title, post.description or "")
        if screen.has_violations:
            raise HTTPException(status_code=400, detail="内容审核未通过")
        review_risk_level = "low"
        if {"title", "description"}.intersection(requested_content):
            review_risk_level = _classification_review(post.title, post.description or "", user_id).get(
                "risk_level",
                "low",
            )
        resolved_risk_level = max(
            (screen.risk_level, review_risk_level),
            key=lambda value: RISK_LEVELS[value],
        )
        if {"title", "description"}.intersection(requested_content) and resolved_risk_level == "high":
            raise HTTPException(status_code=400, detail="内容风险过高，请根据审核建议修改后再保存")
        post.risk_level = resolved_risk_level
        session.add(
            AuditLog(
                user_id=user.id,
                action="post.update",
                target_type="post",
                target_id=str(post.id),
                detail=json.dumps({"fields": sorted(changed)}, ensure_ascii=False),
            )
        )
        try:
            commit_post_participation(session, post)
        except ParticipationError as exc:
            raise _participation_http_error(exc) from exc
        author = session.get(User, post.author_id)
        return api_ok(
            _post_to_dict(post, author, session, viewer_id=user.id),
            "帖子已更新",
        )
    finally:
        session.close()


@router.post("/{post_id}/cover/regenerate")
def regenerate_cover(post_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        post = session.get(Post, post_id)
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        if not can_manage_post(session, user, post, "edit_post"):
            raise HTTPException(status_code=403, detail="你没有编辑该帖子的权限")

        cover_url = generate_content_cover(
            content_type="post",
            title=post.title,
            description=post.description or "",
            category=post.main_category or "校园生活",
            location=post.school_scope or "",
            roles=post.needed_roles or [],
        )
        if not cover_url:
            raise HTTPException(status_code=502, detail="封面生成失败，请稍后重试")

        post.cover_url = cover_url
        session.add(
            AuditLog(
                user_id=user.id,
                action="post.cover.regenerate",
                target_type="post",
                target_id=str(post.id),
                detail=json.dumps({"provider": "coze"}, ensure_ascii=False),
            )
        )
        session.commit()
        session.refresh(post)
        author = session.get(User, post.author_id)
        return api_ok(
            _post_to_dict(post, author, session, viewer_id=user.id),
            "封面已生成",
        )
    finally:
        session.close()


@router.post("/{post_id}/join")
def join(post_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        post = session.scalar(
            select(Post).where(
                Post.id == post_id,
                Post.status.in_(PUBLIC_POST_STATUSES),
            )
        )
        if post is None:
            raise HTTPException(status_code=404, detail="组队不存在")
        try:
            membership = join_post_directly(session, post, user)
            session.commit()
        except ParticipationError as exc:
            session.rollback()
            raise _participation_http_error(exc) from exc
        current_post = session.get(Post, post_id)
        if current_post is None:
            raise HTTPException(status_code=404, detail="组队不存在")
        projection = project_group_cards(session, [current_post], user.id)[0]
        projection["team_id"] = str(membership.team_id)
        projection["member_id"] = str(membership.id)
        return api_ok(projection, "已加入组队")
    finally:
        session.close()


def _transition(post_id: int, user_id: str, action: str) -> dict[str, Any]:
    session = get_session()
    try:
        actor = session.get(User, int(user_id))
        post = session.get(Post, post_id)
        if not actor:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        try:
            transition_post(session, actor, post, action)
            commit_post_participation(session, post)
        except ParticipationError as exc:
            session.rollback()
            raise _participation_http_error(exc) from exc
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        author = session.get(User, post.author_id)
        return api_ok(
            _post_to_dict(post, author, session, viewer_id=actor.id),
            "帖子状态已更新",
        )
    finally:
        session.close()


@router.post("/{post_id}/close")
def close_post(post_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return _transition(post_id, user_id, "close")


@router.post("/{post_id}/reopen")
def reopen_post(post_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return _transition(post_id, user_id, "reopen")


@router.post("/{post_id}/archive")
def archive_post(post_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return _transition(post_id, user_id, "archive")


@router.delete("/{post_id}")
def delete_post(post_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    return _transition(post_id, user_id, "delete")
