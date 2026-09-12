from __future__ import annotations

import datetime
import logging
import math
from copy import deepcopy
from typing import Any, Callable

from sqlalchemy import case, exists, func, literal, literal_column, or_, select, union_all
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
    "attending_topics": [],
    "followed_topics": [],
    "joined_groups": [],
    "group_timeline": [],
    "unread": {"messages": 0, "notifications": 0},
}

RECOMMENDATION_INTEREST_WEIGHT = 100
RECOMMENDATION_MAJOR_WEIGHT = 40
RECOMMENDATION_PARTICIPATION_WEIGHT = 30
RECOMMENDATION_FOLLOW_WEIGHT = 20
TIMELINE_TEAM_LIMIT = 12
TIMELINE_TASKS_PER_TEAM = 12
TIMELINE_ITEM_LIMIT = 12


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


def _ranked_topics_statement(
    interests: list[str], major: str, user_id: int, current: datetime.datetime
):
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
    major_match = case(
        (
            or_(
                exists(
                    select(TopicTag.topic_id)
                    .join(Tag, Tag.id == TopicTag.tag_id)
                    .where(
                        TopicTag.topic_id == Topic.id,
                        Tag.active.is_(True),
                        Tag.canonical_name == major,
                    )
                ),
                Topic.title.contains(major),
                Topic.summary.contains(major),
                Topic.content.contains(major),
            ),
            1,
        ),
        else_=0,
    ) if major else literal(0)
    followed = case(
        (
            exists(
                select(TopicFollow.topic_id).where(
                    TopicFollow.topic_id == Topic.id,
                    TopicFollow.user_id == user_id,
                )
            ),
            1,
        ),
        else_=0,
    )
    participated = case(
        (
            exists(
                select(TeamMember.id)
                .join(Team, Team.id == TeamMember.team_id)
                .join(Post, Post.id == Team.post_id)
                .where(
                    TeamMember.user_id == user_id,
                    Team.status == "active",
                    Post.topic_id == Topic.id,
                )
            ),
            1,
        ),
        else_=0,
    )
    signals = select(
        Topic.id.label("topic_id"),
        overlap_count.label("interest_matches"),
        major_match.label("major_match"),
        participated.label("participated"),
        followed.label("followed"),
    ).where(Topic.status == "active").subquery("recommendation_signals")
    score = (
        signals.c.interest_matches * literal_column(str(RECOMMENDATION_INTEREST_WEIGHT))
        + signals.c.major_match * literal_column(str(RECOMMENDATION_MAJOR_WEIGHT))
        + signals.c.participated * literal_column(str(RECOMMENDATION_PARTICIPATION_WEIGHT))
        + signals.c.followed * literal_column(str(RECOMMENDATION_FOLLOW_WEIGHT))
    )
    next_dates = _next_topic_date_expression(current)
    return (
        select(
            Topic,
            signals.c.interest_matches,
            signals.c.major_match,
            signals.c.participated,
            signals.c.followed,
        )
        .join(signals, signals.c.topic_id == Topic.id)
        .outerjoin(next_dates, next_dates.c.topic_id == Topic.id)
        .order_by(
            score.desc(),
            next_dates.c.next_date.is_(None),
            next_dates.c.next_date.asc(),
            Topic.updated_at.desc(),
            Topic.id.desc(),
        )
        .limit(8)
    )


def _recommended_topics(session: Session, user: User, current: datetime.datetime) -> list[dict[str, Any]]:
    interests = [str(value).strip() for value in (user.interests or []) if str(value).strip()]
    major = str(user.major or "").strip()
    ranked_rows = session.execute(
        _ranked_topics_statement(interests, major, user.id, current)
    ).all()
    topics = [row[0] for row in ranked_rows]
    projections = _batch_topic_projections(session, topics, user.id, current)

    result: list[dict[str, Any]] = []
    for row, projection in zip(ranked_rows, projections):
        topic, _interest_matches, major_match, participated, followed = row
        topic_names = {tag["canonical_name"] for tag in projection["tags"]}
        overlap = [interest for interest in interests if interest in topic_names]
        if overlap:
            reason = f"与你的{'、'.join(overlap)}兴趣相关"
        elif major_match:
            reason = f"与你的{major}专业相关"
        elif participated:
            reason = "基于你正在参加的活动"
        elif followed:
            reason = "你已收藏此活动"
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


def _attending_topics_statement(user_id: int):
    return (
        select(Topic)
        .where(
            Topic.status == "active",
            exists(
                select(TeamMember.id)
                .join(Team, Team.id == TeamMember.team_id)
                .join(Post, Post.id == Team.post_id)
                .where(
                    TeamMember.user_id == user_id,
                    Team.status == "active",
                    Post.topic_id == Topic.id,
                )
            ),
        )
        .order_by(Topic.updated_at.desc(), Topic.id.desc())
        .limit(4)
    )


def _attending_topics(
    session: Session, user: User, current: datetime.datetime
) -> list[dict[str, Any]]:
    topics = list(session.scalars(_attending_topics_statement(user.id)))
    return _batch_topic_projections(session, topics, user.id, current)


def _followed_topics_statement(user_id: int):
    return (
        select(Topic, TopicFollow.created_at)
        .join(TopicFollow, TopicFollow.topic_id == Topic.id)
        .where(TopicFollow.user_id == user_id, Topic.status == "active")
        .order_by(TopicFollow.created_at.desc(), Topic.id.desc())
        .limit(4)
    )


def _followed_topic_rows(session: Session, user: User):
    return session.execute(_followed_topics_statement(user.id)).all()


def _followed_topics(session: Session, user: User, _current: datetime.datetime) -> list[dict[str, Any]]:
    topics = [topic for topic, _followed_at in _followed_topic_rows(session, user)]
    return _batch_topic_projections(session, topics, user.id, _current)


def _deadline_reminder_statement(user_id: int, current: datetime.datetime):
    return (
        select(Topic)
        .join(TopicFollow, TopicFollow.topic_id == Topic.id)
        .where(
            TopicFollow.user_id == user_id,
            Topic.status == "active",
            Topic.registration_deadline > current,
            Topic.registration_deadline <= current + datetime.timedelta(days=14),
        )
        .order_by(Topic.registration_deadline.asc(), Topic.id.desc())
        .limit(1)
    )


def _deadline_reminder(
    session: Session, user: User, current: datetime.datetime
) -> dict[str, Any] | None:
    topic = session.scalars(_deadline_reminder_statement(user.id, current)).first()
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
    for team_id, team_name, task_list in _timeline_team_rows(session, user.id):
        for task in (task_list or [])[:TIMELINE_TASKS_PER_TEAM]:
            if not isinstance(task, dict):
                continue
            due_at = _parse_datetime(task.get("due_at")) or _parse_datetime(
                task.get("deadline")
            )
            items.append(
                (
                    due_at,
                    {
                        "team_id": str(team_id),
                        "team_name": team_name,
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
    return [item for _due_at, item in items[:TIMELINE_ITEM_LIMIT]]


def _timeline_team_rows(session: Session, user_id: int):
    return session.execute(
        select(Team.id, Team.activity_name, Team.task_list)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user_id, Team.status == "active")
        .order_by(TeamMember.created_at.desc(), Team.id.desc())
        .limit(TIMELINE_TEAM_LIMIT)
    ).all()


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
    "attending_topics": _attending_topics,
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
