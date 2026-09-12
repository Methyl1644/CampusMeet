from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from storage.database.models import User


UPDATE_FIELDS = {
    "step",
    "nickname",
    "avatar",
    "major",
    "grade",
    "interests",
    "looking_for",
    "skills",
    "availability",
    "bio",
    "profile_visibility",
}
STRING_LIMITS = {
    "nickname": 40,
    "avatar": 500,
    "major": 80,
    "grade": 40,
    "bio": 500,
}
LIST_LIMITS = {
    "interests": 30,
    "looking_for": 12,
    "skills": 30,
}


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def onboarding_to_dict(user: User) -> dict[str, Any]:
    return {
        "nickname": user.nickname,
        "avatar": user.avatar,
        "major": user.major,
        "grade": user.grade,
        "onboarding_step": user.onboarding_step,
        "onboarding_completed": user.onboarding_completed_at is not None,
        "bio": user.bio,
        "interests": user.interests or [],
        "looking_for": user.looking_for or [],
        "availability": user.availability or {},
        "profile_visibility": user.profile_visibility or {},
        "skills": user.skills or [],
    }


def _normalize_list(field: str, value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} 必须是列表")
    limit = LIST_LIMITS[field]
    if len(value) > limit:
        raise ValueError(f"{field} 最多包含 {limit} 项")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field} 只能包含字符串")
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            normalized.append(item)
    return normalized


def _normalize_mapping(field: str, value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field} 必须是对象")
    if field == "profile_visibility" and not all(
        isinstance(item, bool) for item in value.values()
    ):
        raise ValueError("profile_visibility 的值必须是布尔值")
    return dict(value)


def update_onboarding(
    session: Session,
    user: User,
    payload: Mapping[str, object],
) -> dict[str, Any]:
    del session
    unknown_fields = sorted(set(payload) - UPDATE_FIELDS)
    if unknown_fields:
        raise ValueError(f"包含未知字段: {', '.join(unknown_fields)}")
    if "step" not in payload:
        raise ValueError("缺少 onboarding step")

    requested_step = payload["step"]
    if type(requested_step) is not int:
        raise ValueError("step 必须是整数")

    normalized: dict[str, object] = {}
    for field, limit in STRING_LIMITS.items():
        if field not in payload or payload[field] is None:
            continue
        value = payload[field]
        if not isinstance(value, str):
            raise ValueError(f"{field} 必须是字符串")
        value = value.strip()
        if len(value) > limit:
            raise ValueError(f"{field} 最多 {limit} 个字符")
        normalized[field] = value

    for field in LIST_LIMITS:
        if field in payload and payload[field] is not None:
            normalized[field] = _normalize_list(field, payload[field])

    for field in ("availability", "profile_visibility"):
        if field in payload and payload[field] is not None:
            normalized[field] = _normalize_mapping(field, payload[field])

    current_step = user.onboarding_step or 1
    normalized["onboarding_step"] = max(
        current_step,
        max(1, min(requested_step, 6)),
    )
    for field, value in normalized.items():
        setattr(user, field, value)
    return onboarding_to_dict(user)


def complete_onboarding(session: Session, user: User) -> dict[str, Any]:
    del session
    required_fields = (
        (user.nickname, "请填写昵称"),
        (user.major, "请填写专业"),
        (user.grade, "请填写年级"),
    )
    for value, message in required_fields:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(message)

    unique_interests = {
        item.strip()
        for item in (user.interests or [])
        if isinstance(item, str) and item.strip()
    }
    if len(unique_interests) < 3:
        raise ValueError("至少选择三个兴趣")

    user.onboarding_step = 6
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = utcnow()
    return onboarding_to_dict(user)
