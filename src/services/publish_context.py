from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select

from services.content import FIELD_QUESTIONS, CASUAL_FIELD_QUESTIONS
from services.participation import ParticipationError, validate_post_participation, PURPOSE_JOIN_MODES
from storage.database.models import Tag, Topic, TopicTag

UNKNOWN_TEXT = {"未知", "待定", "暂不确定", "不知道", "不确定", "暂无", "跳过", "先跳过", "待商定", "无", "没有"}


def publish_context(session, user, kind: str, topic_id: str = "") -> dict[str, Any]:
    if user is None or user.account_status != "active":
        raise HTTPException(401, "登录状态已失效")
    if user.auth_status == "unverified":
        raise HTTPException(403, "请先完成校园认证")
    topic = None
    if kind == "topic_team":
        if not str(topic_id).isdigit():
            raise HTTPException(400, "请关联有效活动")
        topic = session.get(Topic, int(topic_id))
        if topic is None or topic.status != "active":
            raise HTTPException(404, "活动已不可用")
    elif kind != "casual_invitation" or topic_id:
        raise HTTPException(400, "发布类型与关联活动不一致")
    allowed, reasons = [], {}
    for purpose in ("team_recruitment", "official_signup", "discussion"):
        try:
            validate_post_participation(session, user, {"topic_id": topic.id if topic else None, "purpose": purpose})
            allowed.append(purpose)
        except ParticipationError as exc:
            reasons[purpose] = exc.message
    tags = []
    if topic:
        tags = [
            {"tag_id": tag.id, "canonical_name": tag.canonical_name, "category": tag.category, "display_color": tag.display_color}
            for tag in session.scalars(select(Tag).join(TopicTag, TopicTag.tag_id == Tag.id).where(TopicTag.topic_id == topic.id).order_by(Tag.id))
        ]
    context = {
        "kind": kind,
        "topic_id": str(topic.id) if topic else None,
        "activity": {"id": str(topic.id), "title": topic.title, "cover_url": topic.cover_url} if topic else None,
        "allowed_purposes": allowed,
        "participation_mode": topic.participation_mode if topic else "open_team",
        "join_modes": {purpose: str(PURPOSE_JOIN_MODES[purpose]) for purpose in allowed},
        "default_purpose": allowed[0],
        "permission_explanations": reasons,
        "inherited_tags": tags,
        "defaults": {"activity_name": topic.title, "deadline": topic.registration_deadline.isoformat() if topic.registration_deadline else ""} if topic else {},
        "max_members": min(10000, max(100, topic.capacity or 0)) if topic else 100,
    }
    context["revision"] = hashlib.sha256(json.dumps(context, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return context


def required_fields(kind: str, purpose: str) -> list[str]:
    if purpose == "discussion":
        return ["activity_name", "description"]
    if purpose == "official_signup":
        return ["activity_name", "target_members", "deadline", "description"]
    return ["activity_name", "target_members", "needed_roles", "weekly_hours", "school_scope"] + (["deadline"] if kind == "topic_team" else [])


def missing_fields(draft: dict, states: dict, kind: str, purpose: str) -> list[str]:
    missing = []
    for field in required_fields(kind, purpose):
        value = draft.get(field)
        status = states.get(field, {}).get("status") if isinstance(states.get(field), dict) else None
        if field == "needed_roles":
            valid = isinstance(value, list) and (bool(value) and all(isinstance(role, str) and role.strip() and role.strip() not in UNKNOWN_TEXT for role in value) or not value and status == "none")
        elif field == "target_members":
            valid = type(value) is int and 1 <= value <= (10000 if purpose == "official_signup" else 100)
        else:
            valid = isinstance(value, str) and bool(value.strip()) and value.strip() not in UNKNOWN_TEXT
        if not valid or status in {"pending", "unknown", "skipped"}:
            missing.append(field)
    return missing


def reconcile_draft(data: dict, previous: dict, context: dict, purpose: str, previous_states: dict | None = None) -> dict:
    result = dict(data)
    draft = {**previous, **(data.get("draft") if isinstance(data.get("draft"), dict) else {})}
    states = {**(previous_states or {}), **dict(data.get("field_states") or {})}
    if not draft.get("description") and previous.get("description"):
        draft["description"] = previous["description"]
        states["description"] = (previous_states or {}).get("description", {"value": previous["description"], "status": "confirmed"})
    if purpose == "official_signup" and type(draft.get("target_members")) is int and draft["target_members"] > context["max_members"]:
        states["target_members"] = {"value": draft["target_members"], "status": "pending"}
    if context["activity"]:
        draft["activity_name"] = context["activity"]["title"]
        states["activity_name"] = {"value": draft["activity_name"], "status": "confirmed"}
    for key in ("topic_id", "purpose", "join_mode"):
        draft.pop(key, None)
    missing = missing_fields(draft, states, context["kind"], purpose)
    questions = dict(FIELD_QUESTIONS if context["kind"] == "topic_team" else CASUAL_FIELD_QUESTIONS)
    questions["description"] = "请补充介绍和参与说明。" if purpose == "official_signup" else "你希望和大家交流什么？"
    result.update(draft=draft, field_states=states, missing_fields=missing, required_fields=required_fields(context["kind"], purpose),
                  is_complete=not missing, next_field=missing[0] if missing else None,
                  reply=questions[missing[0]] if missing else "资料整理好了，请检查和修改，确认后再发布。",
                  purpose=purpose, publish_context_revision=context["revision"], inherited_tags=context["inherited_tags"])
    return result


def inherited_tag_ids(session, topic_id: int | None) -> list[str]:
    return list(session.scalars(select(TopicTag.tag_id).where(TopicTag.topic_id == topic_id).order_by(TopicTag.tag_id))) if topic_id else []


def merge_tag_ids(inherited: list[str], selected: list[str], suggested: list[str] = ()) -> list[str]:
    requested = list(dict.fromkeys([*inherited, *selected]))
    if len(requested) > 8:
        raise ValueError("关联活动标签与附加标签合计最多 8 个")
    return list(dict.fromkeys([*requested, *suggested]))[:8]
