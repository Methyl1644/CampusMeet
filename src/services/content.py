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
OPTIONAL_POST_FIELDS = {"description"}

FIELD_QUESTIONS = {
    "activity_name": "你准备参加或组织什么活动？",
    "target_members": "希望最终组成几个人？请把你自己也算在内。",
    "needed_roles": "希望队友具备哪些能力或负责什么角色？没有要求也可以说“无要求”。",
    "weekly_hours": "每周预计需要投入多少时间？",
    "school_scope": "希望队友来自哪个校区或学院范围？",
    "deadline": "招募或报名截止日期是什么时候？",
}

CASUAL_FIELD_QUESTIONS = {
    **FIELD_QUESTIONS,
    "weekly_hours": "活动计划安排在什么时间？",
    "school_scope": "活动地点准备定在哪里？填写校区或公共场所即可。",
}

_CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_NUMBER_TOKEN = r"[0-9零一二两三四五六七八九十]+"
_EVENT_ACTIVITY_TAGS = {
    "美赛": "activity_math_modeling",
    "挑战杯": "activity_innovation",
    "大创": "activity_innovation",
}


def normalize_text(value: Any) -> str:
    return re.sub(r"[\s\-_/·（）()]+", "", str(value or "").strip().lower())


def _parse_small_number(value: str) -> int | None:
    if value.isdigit():
        parsed = int(value)
        return parsed if 0 < parsed <= 99 else None
    if value == "十":
        return 10
    if "十" in value:
        tens, ones = value.split("十", 1)
        tens_value = _CHINESE_DIGITS.get(tens, 1) if tens else 1
        ones_value = _CHINESE_DIGITS.get(ones, 0) if ones else 0
        parsed = tens_value * 10 + ones_value
        return parsed if 0 < parsed <= 99 else None
    return _CHINESE_DIGITS.get(value)


def _extract_target_members(message: str) -> int | None:
    total_patterns = (
        rf"(?:目标人数|总共|一共|组成|凑齐)(?:是|为)?\s*({_NUMBER_TOKEN})\s*人?",
        rf"({_NUMBER_TOKEN})\s*人成局",
    )
    for pattern in total_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return _parse_small_number(match.group(1))

    recruit = re.search(
        rf"(?:想?找|找到|缺|约|招募?|需要|还差|再来)\s*"
        rf"({_NUMBER_TOKEN})\s*(?:个|位|名)?[^，。；;,.!?！？]{{0,12}}?(?:队友|同学|搭子|人)",
        message,
        re.IGNORECASE,
    )
    if recruit:
        count = _parse_small_number(recruit.group(1))
        return count + 1 if count else None
    if re.search(r"(?:想?找|缺|约)个[^，。；;,.!?！？]{0,12}(?:队友|搭子)", message):
        return 2
    return None


def _extract_direct_target_members(message: str) -> int | None:
    match = re.fullmatch(rf"\s*({_NUMBER_TOKEN})\s*(?:个?人)?\s*", message)
    return _parse_small_number(match.group(1)) if match else None


def _catalog_matches(message: str, categories: set[str]) -> list[str]:
    normalized_message = normalize_text(message)
    matches: list[tuple[int, str]] = []
    normalized_ambiguous = {normalize_text(alias) for alias in AMBIGUOUS_ALIASES}
    for _, canonical_name, category, _, _, aliases in STANDARD_TAGS:
        if category not in categories:
            continue
        terms = (canonical_name, *aliases)
        matched_length = max(
            (
                len(normalized)
                for term in terms
                if (normalized := normalize_text(term))
                and normalized not in normalized_ambiguous
                and normalized in normalized_message
            ),
            default=0,
        )
        if matched_length:
            matches.append((matched_length, canonical_name))
    matches.sort(key=lambda item: item[0], reverse=True)
    return list(dict.fromkeys(name for _, name in matches))


def _extract_activity_name(message: str) -> str | None:
    normalized_message = normalize_text(message)
    for event_name in _EVENT_ACTIVITY_TAGS:
        if normalize_text(event_name) in normalized_message:
            return event_name
    matches = _catalog_matches(message, {"activity"})
    return matches[0] if matches else None


def _extract_time(message: str, kind: str) -> str | None:
    patterns = []
    if kind == "topic_team":
        patterns.append(r"每周(?:大约|预计|投入)?\s*[0-9零一二两三四五六七八九十]+\s*(?:个)?小时")
    patterns.extend(
        (
            r"(?:(?:这|本|下)?周[一二三四五六日天]|周末)(?:的)?(?:早上|上午|中午|下午|晚上|凌晨)?",
            r"(?:今天|明天|后天)(?:的)?(?:早上|上午|中午|下午|晚上|凌晨)?",
        )
    )
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(0).replace("的", "")
    return None


def _extract_deadline(message: str) -> str | None:
    patterns = (
        r"(?:20\d{2}\s*年\s*)?\d{1,2}\s*月\s*\d{1,2}\s*日",
        r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}",
    )
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return re.sub(r"\s+", "", match.group(0))
    return None


def _extract_location(message: str) -> str | None:
    campus = re.search(r"(?:仙林|鼓楼|苏州)(?:校区)?", message)
    place = re.search(
        r"(?:羽毛球馆|篮球场|足球场|乒乓球馆|网球场|图书馆|体育馆|球场|操场|教室|活动室|食堂|线上)",
        message,
    )
    if campus and place:
        return f"{campus.group(0)}{place.group(0)}"
    if campus:
        return campus.group(0)
    if place:
        return place.group(0)
    return None


def _extract_needed_roles(message: str) -> tuple[list[str] | None, str | None]:
    for _, canonical_name, category, _, _, aliases in STANDARD_TAGS:
        if category not in {"role", "skill"}:
            continue
        for term in (canonical_name, *aliases):
            escaped = re.escape(term)
            if re.search(
                rf"(?:不需要|无需|不用)(?:会|掌握|具备)?\s*{escaped}|{escaped}\s*(?:不限|不要求)",
                message,
                re.IGNORECASE,
            ):
                return [], "none"
    matches = _catalog_matches(message, {"role", "skill"})
    if matches:
        return matches[:6], "confirmed"
    normalized = normalize_text(message)
    if normalized in {"无", "没有", "无要求", "不限", "都可以", "都行", "不限制"}:
        return [], "none"
    role_scope = re.search(
        r"(?:技术|水平|能力|经验|性别|男女|专业|年级|参与要求|队友要求|角色)"
        r"[^，。；;,.!?！？]{0,8}(?:无要求|不限|都可以|都行|不限制)",
        message,
    )
    return ([], "none") if role_scope else (None, None)


def _explicit_none_fields(message: str) -> set[str]:
    fields: set[str] = set()
    if re.search(r"(?:地点|校区|学院|范围)[^，。；;,.!?！？]{0,6}(?:不限|都可以|都行|无要求)", message):
        fields.add("school_scope")
    if re.search(r"(?:时间|时段|日期)[^，。；;,.!?！？]{0,6}(?:不限|都可以|都行|无要求)", message):
        fields.add("weekly_hours")
    return fields


def _correction_fields(message: str, extracted_fields: set[str]) -> set[str]:
    marker = re.search(r"(?:改成|改为|更正为|修改为|调整为|其实是|应该是)", message)
    if not marker:
        return set()
    scope = re.split(r"[，。；;,.!?！？]", message[: marker.start()])[-1][-12:]
    field_markers = {
        "activity_name": r"(?:活动|项目|比赛|运动)",
        "target_members": r"(?:人数|几个人|几人)",
        "needed_roles": r"(?:参与要求|队友要求|技术|技能|能力|角色)",
        "weekly_hours": r"(?:活动时间|投入时间|时段|时间|安排)",
        "school_scope": r"(?:活动地点|地点|场地|位置|校区|学院|范围)",
        "deadline": r"(?:截止日期|报名日期|截止)",
    }
    scoped_matches = [
        (len(match.group(0)), field)
        for field, pattern in field_markers.items()
        if (match := re.search(pattern, scope))
    ]
    if scoped_matches:
        longest = max(length for length, _ in scoped_matches)
        return {field for length, field in scoped_matches if length == longest}
    return extracted_fields if len(extracted_fields) == 1 else set()


def _contextual_answer(field: str, message: str) -> Any | None:
    answer = message.strip()
    if not answer or len(answer) > 80 or "\n" in answer:
        return None
    if field == "activity_name":
        return answer
    if field == "target_members":
        return _extract_direct_target_members(answer)
    if field in {"weekly_hours", "school_scope"}:
        return answer
    if field == "needed_roles":
        parts = [part.strip() for part in re.split(r"[、，,和及/]", answer) if part.strip()]
        return parts[:6] or None
    return None


def seed_content_catalog(session: Session) -> None:
    existing_aliases = {
        alias.normalized_alias: alias
        for alias in session.execute(select(TagAlias)).scalars()
    }
    alias_owners: dict[str, set[str]] = {}
    for tag_id, _, _, _, _, aliases in STANDARD_TAGS:
        for alias in aliases:
            alias_owners.setdefault(normalize_text(alias), set()).add(tag_id)
    normalized_ambiguous = {
        normalize_text(alias) for alias in AMBIGUOUS_ALIASES
    } | {
        alias for alias, owners in alias_owners.items() if len(owners) > 1
    }

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
            existing = existing_aliases.get(normalized)
            if normalized in normalized_ambiguous:
                if existing:
                    existing.active = False
                continue
            if not existing:
                existing = TagAlias(tag_id=tag_id, normalized_alias=normalized)
                session.add(existing)
                existing_aliases[normalized] = existing
            else:
                existing.tag_id = tag_id
                existing.active = True
    for normalized in normalized_ambiguous:
        existing = existing_aliases.get(normalized)
        if existing:
            existing.active = False
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
        status = raw.get("status") if isinstance(raw, dict) else (
            "none" if key in OPTIONAL_POST_FIELDS else "pending"
        )
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
    normalized = normalize_text(message)
    pending_before = next(
        (
            key
            for key, value in fields.items()
            if key not in OPTIONAL_POST_FIELDS and value["status"] == "pending"
        ),
        None,
    )

    activity_name = _extract_activity_name(message)
    target_members = _extract_target_members(message)
    if target_members is None and pending_before == "target_members":
        target_members = _extract_direct_target_members(message)
    time_value = _extract_time(message, kind)
    location = _extract_location(message)
    deadline = _extract_deadline(message)
    needed_roles, needed_roles_status = _extract_needed_roles(message)
    extracted = {
        "activity_name": activity_name,
        "target_members": target_members,
        "weekly_hours": time_value,
        "school_scope": location,
        "deadline": deadline,
    }
    present_fields = {key for key, value in extracted.items() if value is not None}
    if needed_roles_status is not None:
        present_fields.add("needed_roles")
    correction_fields = _correction_fields(message, present_fields)
    applied_any = False
    for key, value in extracted.items():
        if (
            key in fields
            and value is not None
            and (fields[key]["status"] == "pending" or key in correction_fields)
        ):
            fields[key] = {"value": value, "status": "confirmed"}
            applied_any = True
    if "needed_roles" in fields and needed_roles_status:
        if (
            fields["needed_roles"]["status"] == "pending"
            or "needed_roles" in correction_fields
            or needed_roles_status == "none"
        ):
            fields["needed_roles"] = {
                "value": needed_roles,
                "status": needed_roles_status,
            }
            applied_any = True

    for field in _explicit_none_fields(message):
        if field in fields:
            fields[field] = {"value": None, "status": "none"}
            applied_any = True

    if pending_before and not applied_any:
        if normalized in {"无", "没有", "不需要", "无需", "无要求"}:
            fields[pending_before] = {"value": None, "status": "none"}
            applied_any = True
        elif normalized in {"不知道", "不确定", "待定", "待商定", "暂无"}:
            fields[pending_before] = {"value": None, "status": "unknown"}
            applied_any = True
        elif normalized in {"跳过", "先跳过", "略过"}:
            fields[pending_before] = {"value": None, "status": "skipped"}
            applied_any = True

    if pending_before and pending_before in previous_fields and not applied_any:
        contextual_value = _contextual_answer(pending_before, message)
        if contextual_value is not None:
            fields[pending_before] = {"value": contextual_value, "status": "confirmed"}

    missing_fields = [
        key
        for key, state in fields.items()
        if key not in OPTIONAL_POST_FIELDS and state["status"] == "pending"
    ]
    next_field = missing_fields[0] if missing_fields else None
    suggested: list[str] = []
    for candidate in candidates:
        tag_id = str(candidate.get("tag_id") or "")
        name = normalize_text(candidate.get("canonical_name"))
        if tag_id and name and (name in normalized or normalized in name):
            suggested.append(tag_id)
        if tag_id and any(
            mapped_tag_id == tag_id and normalize_text(event_name) in normalized
            for event_name, mapped_tag_id in _EVENT_ACTIVITY_TAGS.items()
        ):
            suggested.append(tag_id)
        if tag_id == "activity_badminton" and "羽球" in normalized:
            suggested.append(tag_id)
    suggested = list(dict.fromkeys(suggested))[:4]
    legacy_draft: dict[str, Any] = {
        "activity_name": "",
        "target_members": 0,
        "needed_roles": [],
        "weekly_hours": "",
        "school_scope": "",
        "deadline": "",
        "description": "",
    }
    legacy_draft.update(
        {
            key: (state["value"] if state["status"] == "confirmed" else "")
            for key, state in fields.items()
        }
    )
    if fields.get("needed_roles", {}).get("status") == "none":
        legacy_draft["needed_roles"] = []
    if isinstance(legacy_draft.get("target_members"), str):
        match = re.search(r"(\d+)", legacy_draft["target_members"])
        legacy_draft["target_members"] = int(match.group(1)) if match else 0
    if isinstance(legacy_draft.get("needed_roles"), str):
        legacy_draft["needed_roles"] = [legacy_draft["needed_roles"]] if legacy_draft["needed_roles"] else []
    return {
        "reply": (
            (CASUAL_FIELD_QUESTIONS if kind == "casual_invitation" else FIELD_QUESTIONS)[next_field]
            if next_field
            else "信息已齐全，请确认草稿和标签后发布。"
        ),
        "field_states": fields,
        "draft": legacy_draft,
        "suggested_tag_ids": suggested,
        "candidate_tags": candidates,
        "next_field": next_field,
        "missing_fields": missing_fields,
        "is_complete": next_field is None,
        "degraded": True,
    }
