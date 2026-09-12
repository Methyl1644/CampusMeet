from __future__ import annotations

import datetime
import logging
import math
from copy import deepcopy
from typing import Any, Callable

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from services.content import topic_to_dict
from services.notifications import unread_count as notification_unread_count
from storage.database.models import (
    Conversation,
    Message,
    Post,
    Tag,
    Team,
    TeamMember,
    Topic,
    TopicFollow,
    TopicTag,
    User,
)


logger = logging.getLogger(__name__)

SECTION_DEFAULTS = {
    "deadline_reminder": None,
    "recommended_topics": [],
    "followed_topics": [],
    "joined_groups": [],
    "group_timeline": [],
    "unread": {"messages": 0, "notifications": 0},
}


def ensure_utc(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


def _iso(value: datetime.datetime | None) -> str | None:
    return ensure_utc(value).isoformat() if value is not None else None


def _parse_datetime(value: Any) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return ensure_utc(value)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return ensure_utc(datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00")))
    except ValueError:
        return None


def profile_summary(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "avatar": user.avatar,
        "major": user.major,
        "grade": user.grade,
    }


def _topic_projection(session: Session, topic: Topic, user_id: int) -> dict[str, Any]:
    return {
        **topic_to_dict(session, topic, user_id),
        "registration_deadline": _iso(topic.registration_deadline),
        "activity_start_at": _iso(topic.activity_start_at),
        "activity_end_at": _iso(topic.activity_end_at),
    }


def _next_topic_date(topic: Topic, current: datetime.datetime) -> datetime.datetime | None:
    candidates = [
        ensure_utc(value)
        for value in (
            topic.registration_deadline,
            topic.activity_start_at,
            topic.activity_end_at,
        )
        if value is not None and ensure_utc(value) > current
    ]
    return min(candidates) if candidates else None


def _recommended_topics(session: Session, user: User, current: datetime.datetime) -> list[dict[str, Any]]:
    topics = list(session.scalars(select(Topic).where(Topic.status == "active")))
    if not topics:
        return []

    topic_ids = [topic.id for topic in topics]
    tag_rows = session.execute(
        select(TopicTag.topic_id, Tag.canonical_name)
        .join(Tag, Tag.id == TopicTag.tag_id)
        .where(TopicTag.topic_id.in_(topic_ids), Tag.active.is_(True))
    ).all()
    names_by_topic: dict[int, set[str]] = {}
    for topic_id, name in tag_rows:
        names_by_topic.setdefault(topic_id, set()).add(name)

    interests = [str(value).strip() for value in (user.interests or []) if str(value).strip()]
    ranked: list[tuple[Topic, list[str], datetime.datetime | None]] = []
    for topic in topics:
        topic_names = names_by_topic.get(topic.id, set())
        overlap = [interest for interest in interests if interest in topic_names]
        ranked.append((topic, overlap, _next_topic_date(topic, current)))

    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    ranked.sort(
        key=lambda item: (
            -len(item[1]),
            item[2] is None,
            item[2] or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc),
            -(ensure_utc(item[0].updated_at or epoch) - epoch).total_seconds(),
            -item[0].id,
        )
    )

    result: list[dict[str, Any]] = []
    for topic, overlap, next_date in ranked[:8]:
        if overlap:
            reason = f"与你的{'、'.join(overlap)}兴趣相关"
        elif next_date is not None:
            reason = "近期可参与的校园活动"
        else:
            reason = "近期更新的校园活动"
        result.append(
            {
                **_topic_projection(session, topic, user.id),
                "recommendation_reason": reason,
            }
        )
    return result


def _followed_topic_rows(session: Session, user: User):
    return session.execute(
        select(Topic, TopicFollow.created_at)
        .join(TopicFollow, TopicFollow.topic_id == Topic.id)
        .where(TopicFollow.user_id == user.id, Topic.status == "active")
        .order_by(TopicFollow.created_at.desc(), Topic.id.desc())
    ).all()


def _followed_topics(session: Session, user: User, _current: datetime.datetime) -> list[dict[str, Any]]:
    return [
        _topic_projection(session, topic, user.id)
        for topic, _followed_at in _followed_topic_rows(session, user)[:4]
    ]


def _deadline_reminder(
    session: Session, user: User, current: datetime.datetime
) -> dict[str, Any] | None:
    candidates: list[tuple[datetime.datetime, Topic]] = []
    for topic, _followed_at in _followed_topic_rows(session, user):
        if topic.registration_deadline is None:
            continue
        deadline = ensure_utc(topic.registration_deadline)
        if current < deadline <= current + datetime.timedelta(days=14):
            candidates.append((deadline, topic))
    if not candidates:
        return None

    deadline, topic = min(candidates, key=lambda item: (item[0], -item[1].id))
    return {
        **_topic_projection(session, topic, user.id),
        "days_remaining": math.ceil((deadline - current).total_seconds() / 86400),
    }


def _joined_team_rows(session: Session, user: User, *, limit: int | None = None):
    statement = (
        select(Team, TeamMember, Post)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .join(Post, Post.id == Team.post_id)
        .where(TeamMember.user_id == user.id, Team.status == "active")
        .order_by(TeamMember.created_at.desc(), Team.id.desc())
    )
    if limit is not None:
        statement = statement.limit(limit)
    return session.execute(statement).all()


def _joined_groups(session: Session, user: User, _current: datetime.datetime) -> list[dict[str, Any]]:
    return [
        {
            "id": str(team.id),
            "post_id": str(team.post_id),
            "activity_name": team.activity_name,
            "member_role": membership.member_role,
            "created_at": _iso(membership.created_at),
            "current_members": post.current_members,
            "target_members": post.target_members,
        }
        for team, membership, post in _joined_team_rows(session, user, limit=4)
    ]


def _group_timeline(session: Session, user: User, _current: datetime.datetime) -> list[dict[str, Any]]:
    items: list[tuple[datetime.datetime | None, dict[str, Any]]] = []
    for team, _membership, _post in _joined_team_rows(session, user):
        for task in team.task_list or []:
            if not isinstance(task, dict):
                continue
            due_at = _parse_datetime(task.get("due_at") or task.get("deadline"))
            items.append(
                (
                    due_at,
                    {
                        "team_id": str(team.id),
                        "team_name": team.activity_name,
                        "task_id": str(task.get("id") or ""),
                        "title": str(task.get("title") or ""),
                        "due_at": due_at.isoformat() if due_at else None,
                        "done": bool(task.get("done", False)),
                    },
                )
            )
    items.sort(
        key=lambda item: (
            item[0] is None,
            item[0] or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc),
            item[1]["team_id"],
            item[1]["task_id"],
        )
    )
    return [item for _due_at, item in items[:12]]


def _unread(session: Session, user: User, _current: datetime.datetime) -> dict[str, int]:
    messages = session.scalar(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            or_(Conversation.post_author_id == user.id, Conversation.applicant_id == user.id),
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
    )
    return {
        "messages": int(messages or 0),
        "notifications": notification_unread_count(session, user.id),
    }


HOME_SECTION_BUILDERS: dict[
    str, Callable[[Session, User, datetime.datetime], Any]
] = {
    "deadline_reminder": _deadline_reminder,
    "recommended_topics": _recommended_topics,
    "followed_topics": _followed_topics,
    "joined_groups": _joined_groups,
    "group_timeline": _group_timeline,
    "unread": _unread,
}


def build_home_feed(
    session: Session,
    user: User,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    current = ensure_utc(now or datetime.datetime.now(datetime.timezone.utc))
    result = {
        "profile": profile_summary(user),
        **deepcopy(SECTION_DEFAULTS),
        "warnings": [],
    }
    for name, builder in HOME_SECTION_BUILDERS.items():
        try:
            result[name] = builder(session, user, current)
        except Exception:
            logger.exception(
                "home section failed",
                extra={"section": name, "user_id": user.id},
            )
            result["warnings"].append(name)
    return result
