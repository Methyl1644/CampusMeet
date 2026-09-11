import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from api.common import current_user_id, invoke_tool, parse_tool_result, unwrap_data
from services.content import tag_suggestions
from services.permissions import can_manage_post
from services.tag_governance import sanitize_unknown_concepts, submit_tag_proposal
from storage.database.db import get_session
from storage.database.models import Post, Tag, Team, TeamMember, Topic, User
from tools.ai_tools import (
    ai_classify_review,
    ai_match_teammates,
    ai_post_draft,
    ai_team_plan,
)
from utils.security import screen_content

router = APIRouter(prefix="/agent", tags=["agent"])

VERIFIED_STATUSES = {"verified", "organization", "campus_verified"}


def _positive_id(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{label}不正确") from exc
    if parsed <= 0:
        raise HTTPException(status_code=400, detail=f"{label}不正确")
    return parsed


def _require_verified_user(session, user_id: str) -> User:
    user = session.get(User, _positive_id(user_id, "用户编号"))
    if not user or user.auth_status not in VERIFIED_STATUSES:
        raise HTTPException(status_code=403, detail="请先完成校园认证")
    return user


def _require_post_owner(session, user_id: str, post_id: str) -> Post:
    user = _require_verified_user(session, user_id)
    post = session.get(Post, _positive_id(post_id, "帖子编号"))
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if not can_manage_post(session, user, post, "manage_applications"):
        raise HTTPException(status_code=403, detail="你没有管理该帖子申请的权限")
    return post


def _require_team_member(session, user_id: str, team_id: str) -> Team:
    user = _require_verified_user(session, user_id)
    team = session.get(Team, _positive_id(team_id, "团队编号"))
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    membership = session.execute(
        select(TeamMember).where(
            TeamMember.team_id == team.id,
            TeamMember.user_id == user.id,
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="只有团队成员可以生成团队计划")
    return team


def _candidate_tags(session, message: str = "", limit: int = 120) -> list[dict[str, Any]]:
    try:
        suggested = tag_suggestions(session, message, 12) if message else []
        seen = {item["tag_id"] for item in suggested}
        for tag in session.execute(select(Tag).where(Tag.active.is_(True)).order_by(Tag.sort_order)).scalars():
            if tag.id not in seen:
                suggested.append(
                    {
                        "tag_id": tag.id,
                        "canonical_name": tag.canonical_name,
                        "category": tag.category,
                        "display_color": tag.display_color,
                    }
                )
            if len(suggested) >= limit:
                break
        return suggested[:limit]
    except SQLAlchemyError:
        return []


def store_tag_proposals(
    user_id: str,
    title: str,
    description: str,
    concepts: list[dict[str, Any]],
) -> list[dict[str, str]]:
    proposal_refs: list[dict[str, str]] = []
    proposal_session = get_session()
    try:
        user = _require_verified_user(proposal_session, user_id)
        source_text = f"{title}\n{description}".strip()
        for concept in sanitize_unknown_concepts(concepts):
            try:
                proposal = submit_tag_proposal(
                    proposal_session,
                    user,
                    concept["name"],
                    concept["category"],
                    source_text,
                )
            except ValueError:
                continue
            proposal_refs.append(
                {
                    "proposal_id": str(proposal.id),
                    "name": proposal.proposed_name,
                    "status": proposal.status,
                }
            )
        proposal_session.commit()
        return proposal_refs
    finally:
        proposal_session.close()


@router.post("/post-draft")
def post_draft(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        _require_verified_user(session, user_id)
        kind = str(body.get("kind") or "casual_invitation")
        if kind not in {"topic_team", "casual_invitation"}:
            raise HTTPException(status_code=400, detail="帖子类型不正确")
        topic_id = str(body.get("topic_id") or "")
        if kind == "topic_team" and (not topic_id or not session.get(Topic, int(topic_id))):
            raise HTTPException(status_code=400, detail="正规赛事组队帖必须关联有效话题")
        if kind == "casual_invitation" and topic_id:
            raise HTTPException(status_code=400, detail="日常邀约不能关联正式话题")
        message = str(body.get("message") or "")
        suggested = _candidate_tags(session, message)
    finally:
        session.close()
    draft = body.get("draft") or ""
    skills = body.get("user_skills") or ""
    raw = invoke_tool(
        ai_post_draft,
        {
            "message": body.get("message", ""),
            "draft": draft if isinstance(draft, str) else json.dumps(draft, ensure_ascii=False),
            "user_skills": ",".join(skills) if isinstance(skills, list) else str(skills),
            "kind": kind,
            "field_states": json.dumps(body.get("field_states") or {}, ensure_ascii=False),
            "candidate_tags": json.dumps(suggested, ensure_ascii=False),
            "topic_id": topic_id,
        },
    )
    return parse_tool_result(raw)


@router.post("/classify-review")
def classify_review(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    title = body.get("title") or body.get("activity_name") or ""
    description = body.get("description", "")
    title_screen = screen_content(title)
    description_screen = screen_content(description)
    session = get_session()
    try:
        _require_verified_user(session, user_id)
        candidates = _candidate_tags(session, f"{title} {description}")
    finally:
        session.close()
    raw = invoke_tool(
        ai_classify_review,
        {
            "post_title": title_screen.cleaned_text,
            "post_description": description_screen.cleaned_text,
            "candidate_tags": json.dumps(candidates, ensure_ascii=False),
        },
    )
    result = parse_tool_result(raw)
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    allowed_ids = {str(item.get("tag_id")) for item in candidates}
    returned_ids = data.get("tag_ids")
    data["tag_ids"] = (
        list(dict.fromkeys(str(tag_id) for tag_id in returned_ids if str(tag_id) in allowed_ids))[:8]
        if isinstance(returned_ids, list)
        else []
    )
    concepts = sanitize_unknown_concepts(data.pop("unknown_concepts", []))
    proposal_refs = (
        store_tag_proposals(user_id, title, description, concepts)
        if concepts and body.get("persist_tag_proposals", True)
        else []
    )
    data["unknown_concepts"] = concepts
    data["tag_proposals"] = proposal_refs
    result["data"] = data
    return result


@router.post("/match")
def match(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    post_id = str(body.get("post_id") or "")
    session = get_session()
    try:
        _require_post_owner(session, user_id, post_id)
    finally:
        session.close()
    raw = invoke_tool(ai_match_teammates, {"post_id": post_id})
    data = unwrap_data(raw)
    return {"code": 0, "message": data.get("message", "ok"), "data": {"matches": data.get("matches", [])}}


@router.post("/team-plan")
def team_plan(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    team_id = str(body.get("team_id") or "")
    session = get_session()
    try:
        _require_team_member(session, user_id, team_id)
    finally:
        session.close()
    raw = invoke_tool(ai_team_plan, {"team_id": team_id})
    data = unwrap_data(raw)
    return {"code": 0, "message": data.get("message", "ok"), "data": data.get("team_plan", data)}
