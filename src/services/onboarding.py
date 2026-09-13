from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from services.content_catalog import STANDARD_TAGS
from storage.database.models import User
from storage.database.models.user import DEFAULT_NOTIFICATION_PREFERENCES


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
LIST_ITEM_LIMITS = {
    "interests": 30,
    "looking_for": 40,
    "skills": 80,
}
ONBOARDING_INTERESTS = tuple(
    name for _, name, category, _, _, _ in STANDARD_TAGS if category == "activity"
)
ONBOARDING_INTEREST_SET = frozenset(ONBOARDING_INTERESTS)
AVAILABILITY_FIELDS = frozenset(
    {
        "weekday_daytime",
        "weekday_evening",
        "weekend_daytime",
        "weekend_evening",
        "weekly_hours",
    }
)
LEGACY_AVAILABILITY_FIELDS = {
    "工作日白天": "weekday_daytime",
    "工作日晚间": "weekday_evening",
    "周末白天": "weekend_daytime",
    "周末晚间": "weekend_evening",
}
WEEKLY_HOURS_OPTIONS = frozenset(
    {
        "",
        "每周 1-3 小时",
        "每周 4-6 小时",
        "每周 7-10 小时",
        "每周 10 小时以上",
    }
)
PROFILE_VISIBILITY_FIELDS = frozenset(
    {
        "major",
        "grade",
        "interests",
        "skills",
        "availability",
        "contact",
        "activities",
        "groups",
    }
)
DEFAULT_PROFILE_VISIBILITY = {
    "major": True,
    "grade": True,
    "interests": True,
    "skills": True,
    "availability": False,
    "contact": False,
    "activities": False,
    "groups": False,
}
NOTIFICATION_PREFERENCE_FIELDS = frozenset(DEFAULT_NOTIFICATION_PREFERENCES)
PROFILE_UPDATE_FIELDS = frozenset(
    {
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
        "wechat",
    }
)
MAX_ONBOARDING_TEXT = 4000


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _serialized_availability(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, object] = {}
    for stored_key, item in value.items():
        key = LEGACY_AVAILABILITY_FIELDS.get(stored_key, stored_key)
        if key == "weekly_hours":
            if isinstance(item, str) and item in WEEKLY_HOURS_OPTIONS:
                normalized[key] = item
        elif key in AVAILABILITY_FIELDS and type(item) is bool:
            normalized[key] = item
    return normalized


def onboarding_to_dict(user: User) -> dict[str, Any]:
    profile_visibility = normalized_profile_visibility(user.profile_visibility)
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
        "availability": _serialized_availability(user.availability),
        "profile_visibility": profile_visibility,
        "skills": user.skills or [],
    }


def normalized_profile_visibility(value: object) -> dict[str, bool]:
    stored = value if isinstance(value, Mapping) else {}
    return {
        **DEFAULT_PROFILE_VISIBILITY,
        **{
            key: item
            for key, item in stored.items()
            if key in PROFILE_VISIBILITY_FIELDS and type(item) is bool
        },
    }


def normalize_notification_preferences(value: object) -> dict[str, bool]:
    stored = value if isinstance(value, Mapping) else {}
    return {
        **DEFAULT_NOTIFICATION_PREFERENCES,
        **{
            key: item
            for key, item in stored.items()
            if key in NOTIFICATION_PREFERENCE_FIELDS and type(item) is bool
        },
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
        if not item:
            raise ValueError(f"{field} 不能包含空白项")
        if len(item) > LIST_ITEM_LIMITS[field]:
            raise ValueError(f"{field} 单项最多 {LIST_ITEM_LIMITS[field]} 个字符")
        if field == "interests" and item not in ONBOARDING_INTEREST_SET:
            raise ValueError("interests 只能包含标准兴趣标签")
        if item not in seen:
            seen.add(item)
            normalized.append(item)
    return normalized


def _normalize_mapping(field: str, value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field} 必须是对象")
    allowed_fields = (
        AVAILABILITY_FIELDS if field == "availability" else PROFILE_VISIBILITY_FIELDS
    )
    unknown_fields = sorted(set(value) - allowed_fields)
    if unknown_fields:
        raise ValueError(f"{field} 包含未知字段: {', '.join(unknown_fields)}")
    if field == "profile_visibility":
        if not all(type(item) is bool for item in value.values()):
            raise ValueError("profile_visibility 的值必须是布尔值")
    else:
        for key, item in value.items():
            if key == "weekly_hours":
                if not isinstance(item, str) or item not in WEEKLY_HOURS_OPTIONS:
                    raise ValueError("weekly_hours 不是支持的时间范围")
            elif type(item) is not bool:
                raise ValueError(f"availability.{key} 必须是布尔值")
    return dict(value)


def _text_size(value: object) -> int:
    if isinstance(value, str):
        return len(value)
    if isinstance(value, Mapping):
        return sum(_text_size(item) for item in value.values())
    if isinstance(value, list):
        return sum(_text_size(item) for item in value)
    return 0


def update_profile_fields(user: User, payload: Mapping[str, object]) -> dict[str, Any]:
    unknown_fields = sorted(set(payload) - PROFILE_UPDATE_FIELDS)
    if unknown_fields:
        raise ValueError(f"包含未知字段: {', '.join(unknown_fields)}")
    if _text_size(payload) > MAX_ONBOARDING_TEXT:
        raise ValueError(f"资料文本总量不能超过 {MAX_ONBOARDING_TEXT} 个字符")

    normalized: dict[str, object] = {}
    profile_string_limits = {**STRING_LIMITS, "wechat": 80}
    for field, limit in profile_string_limits.items():
        if field not in payload or payload[field] is None:
            continue
        value = payload[field]
        if not isinstance(value, str):
            raise ValueError(f"{field} 必须是字符串")
        value = value.strip()
        if field in {"nickname", "major", "grade"} and not value:
            raise ValueError(f"{field} 不能为空")
        if len(value) > limit:
            raise ValueError(f"{field} 最多 {limit} 个字符")
        normalized[field] = value or None

    for field in LIST_LIMITS:
        if field in payload and payload[field] is not None:
            normalized[field] = _normalize_list(field, payload[field])

    if "availability" in payload and payload["availability"] is not None:
        normalized["availability"] = _normalize_mapping(
            "availability", payload["availability"]
        )
    if "profile_visibility" in payload and payload["profile_visibility"] is not None:
        visibility = _normalize_mapping(
            "profile_visibility", payload["profile_visibility"]
        )
        normalized["profile_visibility"] = {
            **normalized_profile_visibility(user.profile_visibility),
            **visibility,
        }

    for field, value in normalized.items():
        setattr(user, field, value)
    return profile_settings_to_dict(user)


def profile_settings_to_dict(user: User) -> dict[str, Any]:
    data = onboarding_to_dict(user)
    data.pop("onboarding_step", None)
    data.pop("onboarding_completed", None)
    data["wechat"] = user.wechat
    data["notification_preferences"] = normalize_notification_preferences(
        user.notification_preferences
    )
    return data


def update_settings(
    user: User,
    payload: Mapping[str, object],
) -> dict[str, Any]:
    allowed = {"profile_visibility", "notification_preferences"}
    unknown_fields = sorted(set(payload) - allowed)
    if unknown_fields:
        raise ValueError(f"包含未知字段: {', '.join(unknown_fields)}")
    if "profile_visibility" in payload and payload["profile_visibility"] is not None:
        patch = _normalize_mapping("profile_visibility", payload["profile_visibility"])
        user.profile_visibility = {
            **normalized_profile_visibility(user.profile_visibility),
            **patch,
        }
    if (
        "notification_preferences" in payload
        and payload["notification_preferences"] is not None
    ):
        value = payload["notification_preferences"]
        if not isinstance(value, dict):
            raise ValueError("notification_preferences 必须是对象")
        unknown = sorted(set(value) - NOTIFICATION_PREFERENCE_FIELDS)
        if unknown:
            raise ValueError(
                f"notification_preferences 包含未知字段: {', '.join(unknown)}"
            )
        if not all(type(item) is bool for item in value.values()):
            raise ValueError("notification_preferences 的值必须是布尔值")
        user.notification_preferences = {
            **normalize_notification_preferences(user.notification_preferences),
            **value,
        }
    return profile_settings_to_dict(user)


def update_onboarding(
    session: Session,
    user: User,
    payload: Mapping[str, object],
) -> dict[str, Any]:
    del session
    if user.onboarding_completed_at is not None:
        raise ValueError("资料已完成，不能修改 onboarding 草稿")

    unknown_fields = sorted(set(payload) - UPDATE_FIELDS)
    if unknown_fields:
        raise ValueError(f"包含未知字段: {', '.join(unknown_fields)}")
    if "step" not in payload:
        raise ValueError("缺少 onboarding step")
    if _text_size(payload) > MAX_ONBOARDING_TEXT:
        raise ValueError(f"onboarding 文本总量不能超过 {MAX_ONBOARDING_TEXT} 个字符")

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
            mapping = _normalize_mapping(field, payload[field])
            if field == "profile_visibility":
                stored_visibility = user.profile_visibility or {}
                normalized[field] = {
                    **DEFAULT_PROFILE_VISIBILITY,
                    **{
                        key: value
                        for key, value in stored_visibility.items()
                        if key in PROFILE_VISIBILITY_FIELDS and type(value) is bool
                    },
                    **mapping,
                }
            else:
                normalized[field] = mapping

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
    if not unique_interests <= ONBOARDING_INTEREST_SET:
        raise ValueError("interests 只能包含标准兴趣标签")
    if len(unique_interests) < 3:
        raise ValueError("至少选择三个兴趣")

    user.onboarding_step = 6
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = utcnow()
    return onboarding_to_dict(user)
