import datetime
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from storage.database.models import (
    Organization,
    OrganizationMember,
    Tag,
    TagAlias,
    Topic,
    TopicFollow,
    TopicTag,
    User,
)
from services.content_catalog import AMBIGUOUS_ALIASES, STANDARD_TAGS

POST_FIELDS = {
    "topic_team": (
        "activity_name",
        "target_members",
        "needed_roles",
        "weekly_hours",
        "school_scope",
        "deadline",
        "description",
    ),
    "casual_invitation": (
        "activity_name",
        "target_members",
        "weekly_hours",
        "school_scope",
        "needed_roles",
        "description",
    ),
}
TERMINAL_FIELD_STATUSES = {"confirmed", "none", "unknown", "skipped"}


def normalize_text(value: Any) -> str:
    return re.sub(r"[\s\-_/·（）()]+", "", str(value or "").strip().lower())


def seed_content_catalog(session: Session) -> None:
    for tag_id, name, category, color, order, aliases in STANDARD_TAGS:
        tag = session.get(Tag, tag_id)
        if not tag:
            tag = Tag(
                id=tag_id,
                canonical_name=name,
                category=category,
                display_color=color,
                sort_order=order,
            )
            session.add(
                tag
            )
        else:
            tag.canonical_name = name
            tag.category = category
            tag.display_color = color
            tag.sort_order = order
            tag.active = True
        for alias in aliases:
            normalized = normalize_text(alias)
            existing = session.execute(
                select(TagAlias).where(TagAlias.normalized_alias == normalized)
            ).scalar_one_or_none()
            if not existing:
                session.add(TagAlias(tag_id=tag_id, normalized_alias=normalized))
            else:
                existing.tag_id = tag_id
                existing.active = True
    normalized_ambiguous = {normalize_text(alias) for alias in AMBIGUOUS_ALIASES}
    for alias in session.execute(
        select(TagAlias).where(TagAlias.normalized_alias.in_(normalized_ambiguous))
    ).scalars():
        alias.active = False
    session.flush()


def bootstrap_operator(session: Session, email: str) -> bool:
    """Promote one explicitly configured, already registered account."""
    normalized = email.strip().lower()
    if not normalized:
        return False
    user = session.execute(
        select(User).where(or_(User.email == normalized, User.verified_email == normalized))
    ).scalar_one_or_none()
    if not user:
        return False
    user.site_role = "operator"
    return True


def _active_tag_rows(session: Session) -> list[tuple[Tag, list[str]]]:
    tags = session.execute(
        select(Tag).where(Tag.active.is_(True)).order_by(Tag.sort_order, Tag.canonical_name)
    ).scalars().all()
    aliases = session.execute(select(TagAlias).where(TagAlias.active.is_(True))).scalars().all()
    by_tag: dict[str, list[str]] = {}
    for alias in aliases:
        by_tag.setdefault(alias.tag_id, []).append(alias.normalized_alias)
    return [(tag, by_tag.get(tag.id, [])) for tag in tags]


def tag_suggestions(session: Session, query: str, limit: int = 8) -> list[dict[str, Any]]:
    normalized = normalize_text(query)
    if not normalized:
        return []
    ranked: list[tuple[int, dict[str, Any]]] = []
    for tag, aliases in _active_tag_rows(session):
        canonical = normalize_text(tag.canonical_name)
        matched_alias = next((alias for alias in aliases if alias == normalized), None)
        if canonical == normalized:
            rank = 0
        elif matched_alias:
            rank = 1
        elif canonical.startswith(normalized):
            rank = 2
        elif any(alias.startswith(normalized) for alias in aliases):
            rank = 3
            matched_alias = next(alias for alias in aliases if alias.startswith(normalized))
        elif normalized in canonical:
            rank = 4
        elif any(normalized in alias for alias in aliases):
            rank = 5
            matched_alias = next(alias for alias in aliases if normalized in alias)
        else:
            continue
        ranked.append(
            (
                rank,
                {
                    "tag_id": tag.id,
                    "canonical_name": tag.canonical_name,
                    "category": tag.category,
                    "display_color": tag.display_color,
                    "matched_alias": query if matched_alias else None,
                },
            )
        )
    ranked.sort(key=lambda item: (item[0], item[1]["canonical_name"]))
    return [item for _, item in ranked[:limit]]


def suggest_content(session: Session, query: str, channel: str = "") -> dict[str, list[dict[str, Any]]]:
    normalized = normalize_text(query)
    direct: list[dict[str, Any]] = []
    if normalized:
        topics = session.execute(
            select(Topic).where(Topic.status == "active").order_by(Topic.updated_at.desc())
        ).scalars().all()
        for topic in topics:
            if channel in {"official", "organization"} and topic.channel != channel:
                continue
            haystacks = (topic.title, topic.short_title, topic.organizer, topic.canonical_event_key)
            matches = [normalize_text(value) for value in haystacks]
            if any(normalized in value or value in normalized for value in matches if value):
                direct.append(
                    {
                        "entity_type": "topic",
                        "entity_id": str(topic.id),
                        "title": topic.title,
                        "subtitle": topic.organizer,
                        "matched_by": "keyword",
                        "channel": topic.channel,
                    }
                )
        direct = direct[:6]
    return {"direct": direct, "tags": tag_suggestions(session, query, 6)}


def _aware_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _is_active_membership(member: OrganizationMember) -> bool:
    if member.status != "active" or member.role not in {"owner", "publisher"}:
        return False
    if member.expires_at is None:
        return True
    expires = member.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=datetime.timezone.utc)
    return expires > _aware_now()


def user_permissions(session: Session, user: User) -> dict[str, Any]:
    memberships = session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    ).scalars().all()
    publisher_org_ids = [str(member.organization_id) for member in memberships if _is_active_membership(member)]
    campus_verified = user.auth_status in {"verified", "organization", "campus_verified"}
    return {
        "campus_verified": campus_verified,
        "site_role": user.site_role,
        "can_publish_post": campus_verified,
        "can_publish_official_topic": user.site_role == "operator",
        "publisher_organization_ids": publisher_org_ids,
    }


def validate_tag_ids(session: Session, tag_ids: list[str]) -> list[str]:
    clean = list(dict.fromkeys(tag_ids))[:8]
    if not clean:
        return []
    found = set(
        session.execute(select(Tag.id).where(Tag.id.in_(clean), Tag.active.is_(True))).scalars().all()
    )
    return [tag_id for tag_id in clean if tag_id not in found]


def _event_key(payload: dict[str, Any]) -> str:
    return normalize_text(payload.get("canonical_event_key") or payload.get("short_title") or payload.get("title"))


def create_topic(session: Session, user: User, payload: dict[str, Any]) -> Topic:
    channel = str(payload.get("channel") or "")
    organization_id = payload.get("organization_id")
    if channel == "official":
        if user.site_role != "operator":
            raise PermissionError("官方话题仅平台运营账号可以发布")
        organization_id = None
    elif channel == "organization":
        if not organization_id:
            raise ValueError("组织话题必须指定组织")
        org = session.get(Organization, int(organization_id))
        if not org or org.verification_status != "approved":
            raise PermissionError("组织尚未通过认证")
        member = session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == user.id,
            )
        ).scalar_one_or_none()
        if not member or not _is_active_membership(member):
            raise PermissionError("只有该组织的有效发布者可以发布话题")
    else:
        raise ValueError("话题频道必须是 official 或 organization")

    title = str(payload.get("title") or "").strip()
    short_title = str(payload.get("short_title") or title).strip()
    organizer = str(payload.get("organizer") or "").strip()
    edition = str(payload.get("edition") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    content = str(payload.get("content") or "").strip()
    if not all((title, short_title, organizer, edition, summary, content)):
        raise ValueError("请完整填写话题名称、主办方、届次、简介和资料")
    tag_ids = [str(item) for item in payload.get("tag_ids") or []]
    invalid = validate_tag_ids(session, tag_ids)
    if invalid:
        raise ValueError(f"包含未收录的标签：{', '.join(invalid)}")
    if not tag_ids:
        raise ValueError("请至少选择一个标准标签")

    organizer_key = normalize_text(organizer)
    event_key = _event_key(payload)
    duplicate = session.execute(
        select(Topic).where(
            Topic.organizer_key == organizer_key,
            Topic.canonical_event_key == event_key,
            Topic.edition == edition,
        )
    ).scalar_one_or_none()
    if duplicate:
        raise ValueError("同一主办方、活动和届次的话题已存在")

    topic = Topic(
        channel=channel,
        title=title,
        short_title=short_title,
        organizer=organizer,
        organizer_key=organizer_key,
        canonical_event_key=event_key,
        edition=edition,
        summary=summary,
        content=content,
        source_url=str(payload.get("source_url") or "").strip() or None,
        cover_url=str(payload.get("cover_url") or "").strip() or None,
        organization_id=int(organization_id) if organization_id else None,
        created_by=user.id,
    )
    session.add(topic)
    session.flush()
    session.add_all(TopicTag(topic_id=topic.id, tag_id=tag_id) for tag_id in tag_ids)
    return topic


def topic_to_dict(session: Session, topic: Topic, user_id: int | None = None) -> dict[str, Any]:
    tags = session.execute(
        select(Tag).join(TopicTag, TopicTag.tag_id == Tag.id).where(TopicTag.topic_id == topic.id)
    ).scalars().all()
    follower_count = session.scalar(
        select(func.count()).select_from(TopicFollow).where(TopicFollow.topic_id == topic.id)
    ) or 0
    followed = False
    if user_id is not None:
        followed = session.get(TopicFollow, {"topic_id": topic.id, "user_id": user_id}) is not None
    return {
        "id": str(topic.id),
        "channel": topic.channel,
        "title": topic.title,
        "short_title": topic.short_title,
        "organizer": topic.organizer,
        "edition": topic.edition,
        "summary": topic.summary,
        "content": topic.content,
        "source_url": topic.source_url,
        "source_status": topic.source_status,
        "cover_url": topic.cover_url,
        "follower_count": follower_count,
        "followed": followed,
        "tags": [
            {
                "tag_id": tag.id,
                "canonical_name": tag.canonical_name,
                "category": tag.category,
                "display_color": tag.display_color,
            }
            for tag in tags
        ],
        "status": topic.status,
    }


def _initial_field_states(kind: str, previous_fields: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = POST_FIELDS.get(kind, POST_FIELDS["casual_invitation"])
    result: dict[str, dict[str, Any]] = {}
    for key in fields:
        raw = previous_fields.get(key) if isinstance(previous_fields, dict) else None
        status = raw.get("status") if isinstance(raw, dict) else "pending"
        if status not in TERMINAL_FIELD_STATUSES | {"pending"}:
            status = "pending"
        value = raw.get("value") if isinstance(raw, dict) else None
        result[key] = {"value": value if status == "confirmed" else None, "status": status}
    return result


def build_post_draft(
    *,
    kind: str,
    message: str,
    previous_fields: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    fields = _initial_field_states(kind, previous_fields)
    pending = next((key for key, value in fields.items() if value["status"] == "pending"), None)
    normalized = normalize_text(message)
    if pending and normalized in {"无", "没有", "不需要", "无需"}:
        fields[pending] = {"value": None, "status": "none"}
    elif pending and normalized in {"不知道", "不确定", "待定", "待商定", "暂无"}:
        fields[pending] = {"value": None, "status": "unknown"}
    elif pending and normalized in {"跳过", "先跳过", "略过"}:
        fields[pending] = {"value": None, "status": "skipped"}
    elif pending and message.strip():
        fields[pending] = {"value": message.strip()[:120], "status": "confirmed"}

    next_field = next((key for key, value in fields.items() if value["status"] == "pending"), None)
    suggested: list[str] = []
    for candidate in candidates:
        tag_id = str(candidate.get("tag_id") or "")
        name = normalize_text(candidate.get("canonical_name"))
        if tag_id and name and (name in normalized or normalized in name):
            suggested.append(tag_id)
        if tag_id == "activity_badminton" and "羽球" in normalized:
            suggested.append(tag_id)
    suggested = list(dict.fromkeys(suggested))[:4]
    legacy_draft: dict[str, Any] = {
        "activity_name": "",
        "target_members": 1,
        "needed_roles": [],
        "weekly_hours": "",
        "school_scope": "",
        "deadline": "",
        "description": "",
    }
    legacy_draft.update({
        key: (state["value"] if state["status"] == "confirmed" else "")
        for key, state in fields.items()
    })
    if isinstance(legacy_draft.get("target_members"), str):
        match = re.search(r"(\d+)", legacy_draft["target_members"])
        legacy_draft["target_members"] = int(match.group(1)) if match else 1
    if isinstance(legacy_draft.get("needed_roles"), str):
        legacy_draft["needed_roles"] = [legacy_draft["needed_roles"]] if legacy_draft["needed_roles"] else []
    return {
        "reply": "信息已整理，请继续补充。" if next_field else "信息已齐全，请确认标签后发布。",
        "field_states": fields,
        "draft": legacy_draft,
        "suggested_tag_ids": suggested,
        "candidate_tags": candidates,
        "next_field": next_field,
        "missing_fields": [key for key, state in fields.items() if state["status"] == "pending"],
        "is_complete": next_field is None,
        "degraded": True,
    }
