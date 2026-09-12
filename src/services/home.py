from __future__ import annotations

import datetime
import logging
import math
from copy import deepcopy
from typing import Any, Callable

from sqlalchemy import case, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from services.identity import organization_is_active
from services.notifications import unread_count as notification_unread_count
from storage.database.models import (
    Conversation,
    Message,
    Organization,
    Post,
    Tag,
    Team,
    TeamMember,
    Topic,
    TopicCollaborator,
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


def _next_topic_date_expression(current: datetime.datetime) -> Any:
    future_dates = union_all(
        select(
            Topic.id.label("topic_id"),
            Topic.registration_deadline.label("event_date"),
        ).where(Topic.registration_deadline > current),
        select(
            Topic.id.label("topic_id"),
            Topic.activity_start_at.label("event_date"),
        ).where(Topic.activity_start_at > current),
        select(
            Topic.id.label("topic_id"),
            Topic.activity_end_at.label("event_date"),
        ).where(Topic.activity_end_at > current),
    ).subquery()
    return (
        select(
            future_dates.c.topic_id,
            func.min(future_dates.c.event_date).label("next_date"),
        )
        .group_by(future_dates.c.topic_id)
        .subquery()
    )


def _batch_topic_projections(
    session: Session,
    topics: list[Topic],
    user_id: int,
    current: datetime.datetime,
) -> list[dict[str, Any]]:
    if not topics:
        return []

    topic_ids = [topic.id for topic in topics]
    tags_by_topic: dict[int, list[dict[str, str]]] = {topic_id: [] for topic_id in topic_ids}
    tag_rows = session.execute(
        select(TopicTag.topic_id, Tag)
        .join(Tag, Tag.id == TopicTag.tag_id)
        .where(TopicTag.topic_id.in_(topic_ids))
        .order_by(Tag.sort_order, Tag.canonical_name, Tag.id)
    ).all()
    for topic_id, tag in tag_rows:
        tags_by_topic[topic_id].append(
            {
                "tag_id": tag.id,
                "canonical_name": tag.canonical_name,
                "category": tag.category,
                "display_color": tag.display_color,
            }
        )

    follow_metadata = {
        topic_id: (int(follower_count), bool(followed))
        for topic_id, follower_count, followed in session.execute(
            select(
                TopicFollow.topic_id,
                func.count(),
                func.max(case((TopicFollow.user_id == user_id, 1), else_=0)),
            )
            .where(TopicFollow.topic_id.in_(topic_ids))
            .group_by(TopicFollow.topic_id)
        ).all()
    }

    responsible_by_topic: dict[int, list[dict[str, str]]] = {
        topic_id: [] for topic_id in topic_ids
    }
    collaborator_rows = session.execute(
        select(TopicCollaborator, User)
        .join(User, User.id == TopicCollaborator.user_id)
        .where(
            TopicCollaborator.topic_id.in_(topic_ids),
            TopicCollaborator.status == "active",
            or_(
                TopicCollaborator.expires_at.is_(None),
                TopicCollaborator.expires_at > current,
            ),
        )
        .order_by(TopicCollaborator.topic_id, TopicCollaborator.id)
    ).all()
    for collaborator, collaborator_user in collaborator_rows:
        responsible_by_topic[collaborator.topic_id].append(
            {
                "user_id": str(collaborator_user.id),
                "nickname": collaborator_user.nickname,
                "role": collaborator.role,
                "badge": "活动负责人",
            }
        )

    organization_ids = {
        topic.organization_id for topic in topics if topic.organization_id is not None
    }
    organizations = (
        {
            organization.id: organization
            for organization in session.scalars(
                select(Organization).where(Organization.id.in_(organization_ids))
            )
        }
        if organization_ids
        else {}
    )

    projections: list[dict[str, Any]] = []
    for topic in topics:
        follower_count, followed = follow_metadata.get(topic.id, (0, False))
        trust_badges: list[dict[str, str]] = []
        if topic.channel == "official":
            trust_badges.append({"kind": "platform_official", "label": "平台官方收录"})
        elif topic.channel == "organization" and topic.organization_id:
            organization = organizations.get(topic.organization_id)
            if organization and organization_is_active(organization, now=current):
                trust_badges.append(
                    {
                        "kind": "verified_organization",
                        "label": "认证组织发布",
                        "organization_name": organization.name,
                    }
                )
        projections.append(
            {
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
                "tags": tags_by_topic[topic.id],
                "status": topic.status,
                "trust_badges": trust_badges,
                "responsible_people": responsible_by_topic[topic.id],
                "registration_deadline": _iso(topic.registration_deadline),
                "activity_start_at": _iso(topic.activity_start_at),
                "activity_end_at": _iso(topic.activity_end_at),
            }
        )
    return projections


def _recommended_topics(session: Session, user: User, current: datetime.datetime) -> list[dict[str, Any]]:
    interests = [str(value).strip() for value in (user.interests or []) if str(value).strip()]
    overlap_count = (
        select(func.count(TopicTag.tag_id))
        .join(Tag, Tag.id == TopicTag.tag_id)
        .where(
            TopicTag.topic_id == Topic.id,
            Tag.active.is_(True),
            Tag.canonical_name.in_(interests),
        )
        .correlate(Topic)
        .scalar_subquery()
        if interests
        else literal(0)
    )
    next_dates = _next_topic_date_expression(current)
    topics = list(
        session.scalars(
            select(Topic)
            .outerjoin(next_dates, next_dates.c.topic_id == Topic.id)
            .where(Topic.status == "active")
            .order_by(
                overlap_count.desc(),
                next_dates.c.next_date.is_(None),
                next_dates.c.next_date.asc(),
                Topic.updated_at.desc(),
                Topic.id.desc(),
            )
            .limit(8)
        )
    )
    projections = _batch_topic_projections(session, topics, user.id, current)

    result: list[dict[str, Any]] = []
    for topic, projection in zip(topics, projections):
        topic_names = {tag["canonical_name"] for tag in projection["tags"]}
        overlap = [interest for interest in interests if interest in topic_names]
        if overlap:
            reason = f"与你的{'、'.join(overlap)}兴趣相关"
        elif any(
            value is not None and ensure_utc(value) > current
            for value in (
                topic.registration_deadline,
                topic.activity_start_at,
                topic.activity_end_at,
            )
        ):
            reason = "近期可参与的校园活动"
        else:
            reason = "近期更新的校园活动"
        result.append({**projection, "recommendation_reason": reason})
    return result


def _followed_topic_rows(session: Session, user: User):
    return session.execute(
        select(Topic, TopicFollow.created_at)
        .join(TopicFollow, TopicFollow.topic_id == Topic.id)
        .where(TopicFollow.user_id == user.id, Topic.status == "active")
        .order_by(TopicFollow.created_at.desc(), Topic.id.desc())
        .limit(4)
    ).all()


def _followed_topics(session: Session, user: User, _current: datetime.datetime) -> list[dict[str, Any]]:
    topics = [topic for topic, _followed_at in _followed_topic_rows(session, user)]
    return _batch_topic_projections(session, topics, user.id, _current)


def _deadline_reminder(
    session: Session, user: User, current: datetime.datetime
) -> dict[str, Any] | None:
    topic = session.scalars(
        select(Topic)
        .join(TopicFollow, TopicFollow.topic_id == Topic.id)
        .where(
            TopicFollow.user_id == user.id,
            Topic.status == "active",
            Topic.registration_deadline > current,
            Topic.registration_deadline <= current + datetime.timedelta(days=14),
        )
        .order_by(Topic.registration_deadline.asc(), Topic.id.desc())
        .limit(1)
    ).first()
    if topic is None:
        return None

    deadline = ensure_utc(topic.registration_deadline)
    return {
        **_batch_topic_projections(session, [topic], user.id, current)[0],
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
            due_at = _parse_datetime(task.get("due_at")) or _parse_datetime(
                task.get("deadline")
            )
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
            session.rollback()
            result["warnings"].append(name)
    return result
