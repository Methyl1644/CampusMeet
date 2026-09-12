from __future__ import annotations

import datetime
import math
from collections import defaultdict
from typing import Any, Sequence

from sqlalchemy import Date, DateTime, Integer, and_, case, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from services.collaboration_lifecycle import PUBLIC_POST_STATUSES
from services.identity import organization_is_active
from services.participation import deadline_has_passed
from storage.database.models import (
    Application,
    Organization,
    Post,
    PostBookmark,
    PostCollaborator,
    PostTag,
    Tag,
    Team,
    TeamMember,
    Topic,
    TopicCollaborator,
    TopicFollow,
    TopicTag,
    User,
)


MAX_PAGE_SIZE = 40
PREVIEW_LIMIT = 8
RELATED_GROUP_LIMIT = 8
FORMAL_ACTIVITY_CHANNELS = ("official", "organization")

CATEGORY_PLACEHOLDER_KEYS = {
    "竞赛与项目": "category:competition-project",
    "学习与科研": "category:study-research",
    "体育与健身": "category:sports-fitness",
    "旅行与户外": "category:travel-outdoor",
    "校园生活": "category:campus-life",
    "拼团与AA": "category:group-buying",
}

POSTGRES_DATE_ONLY_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
POSTGRES_ZONED_DATETIME_PATTERN = (
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt ][0-9]{2}:[0-9]{2}"
    r"(:[0-9]{2}(\.[0-9]{1,6})?)?([Zz]|[+-][0-9]{2}:[0-9]{2})$"
)


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _ensure_utc(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


def _iso(value: datetime.datetime | None) -> str | None:
    return _ensure_utc(value).isoformat() if value is not None else None


def _selected_tags(tag_ids: Sequence[str] | str | None) -> list[str]:
    values = tag_ids.split(",") if isinstance(tag_ids, str) else tag_ids or []
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))[:8]


def _pagination(page: int, page_size: int) -> tuple[int, int]:
    return max(1, int(page)), min(MAX_PAGE_SIZE, max(1, int(page_size)))


def _page(items: list[dict[str, Any]], total: int, page: int, page_size: int) -> dict[str, Any]:
    return {
        "list": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


def _deadline_range_predicate(
    date_filter: str,
    now: datetime.datetime,
    dialect_name: str,
):
    if dialect_name == "postgresql":
        parsed_deadline = case(
            (
                Post.deadline.op("~")(POSTGRES_DATE_ONLY_PATTERN),
                func.timezone(
                    "UTC",
                    cast(cast(Post.deadline, Date), DateTime(timezone=False)),
                ),
            ),
            (
                Post.deadline.op("~")(POSTGRES_ZONED_DATETIME_PATTERN),
                cast(Post.deadline, DateTime(timezone=True)),
            ),
            else_=None,
        )
        comparison_time: Any = _ensure_utc(now)
    else:
        parsed_deadline = func.julianday(Post.deadline)
        comparison_time = func.julianday(_ensure_utc(now).isoformat())

    if date_filter == "upcoming":
        return or_(Post.deadline.is_(None), parsed_deadline >= comparison_time)
    if date_filter in {"past", "ended"}:
        return and_(
            Post.deadline.is_not(None),
            parsed_deadline.is_not(None),
            parsed_deadline < comparison_time,
        )
    return None


def _user_summary(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "avatar": user.avatar,
        "major": user.major,
        "grade": user.grade,
    }


def activity_placeholder_key(topic: Topic) -> str:
    return f"activity:{topic.channel}"


def group_placeholder_key(post: Post) -> str:
    return CATEGORY_PLACEHOLDER_KEYS.get(post.main_category, "category:campus-life")


def _tag_projection(tag: Tag) -> dict[str, str]:
    return {
        "tag_id": tag.id,
        "canonical_name": tag.canonical_name,
        "category": tag.category,
        "display_color": tag.display_color,
    }


def _participant_count_rows(
    session: Session, topic_ids: Sequence[int]
) -> list[Any]:
    return session.execute(
        select(
            Post.topic_id,
            func.count(func.distinct(TeamMember.user_id)),
        )
        .join(Team, Team.post_id == Post.id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(
            Post.topic_id.in_(topic_ids),
            Post.status.in_(PUBLIC_POST_STATUSES),
            Team.status == "active",
        )
        .group_by(Post.topic_id)
    ).all()


def _participant_preview_rows(
    session: Session, topic_ids: Sequence[int]
) -> list[Any]:
    unique_participants = (
        select(
            Post.topic_id.label("topic_id"),
            TeamMember.user_id.label("user_id"),
            func.min(TeamMember.created_at).label("joined_at"),
        )
        .join(Team, Team.post_id == Post.id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(
            Post.topic_id.in_(topic_ids),
            Post.status.in_(PUBLIC_POST_STATUSES),
            Team.status == "active",
        )
        .group_by(Post.topic_id, TeamMember.user_id)
        .subquery()
    )
    ranked = (
        select(
            unique_participants.c.topic_id,
            unique_participants.c.user_id,
            unique_participants.c.joined_at,
            func.row_number()
            .over(
                partition_by=unique_participants.c.topic_id,
                order_by=(
                    unique_participants.c.joined_at,
                    unique_participants.c.user_id,
                ),
            )
            .label("preview_rank"),
        )
        .subquery()
    )
    return session.execute(
        select(ranked.c.topic_id, ranked.c.joined_at, User)
        .join(User, User.id == ranked.c.user_id)
        .where(ranked.c.preview_rank <= PREVIEW_LIMIT)
        .order_by(ranked.c.topic_id, ranked.c.preview_rank)
    ).all()


def _activity_state_rows(
    session: Session,
    topic_ids: Sequence[int],
    user_id: int,
    *,
    now: datetime.datetime,
) -> list[Any]:
    public_post = (
        Post.topic_id == Topic.id,
        Post.status.in_(PUBLIC_POST_STATUSES),
    )
    owner = exists(select(Post.id).where(*public_post, Post.author_id == user_id))
    joined = exists(
        select(TeamMember.id)
        .join(Team, Team.id == TeamMember.team_id)
        .join(Post, Post.id == Team.post_id)
        .where(
            *public_post,
            Team.status == "active",
            TeamMember.user_id == user_id,
        )
    )
    pending = exists(
        select(Application.id)
        .join(Post, Post.id == Application.post_id)
        .where(
            *public_post,
            Application.applicant_id == user_id,
            Application.status.in_(("pending", "accepted")),
        )
    )
    rejected = exists(
        select(Application.id)
        .join(Post, Post.id == Application.post_id)
        .where(
            *public_post,
            Application.applicant_id == user_id,
            Application.status == "rejected",
        )
    )
    deadline_is_open = _deadline_range_predicate(
        "upcoming", now, session.get_bind().dialect.name
    )
    available = exists(
        select(Post.id).where(
            Post.topic_id == Topic.id,
            Post.status == "recruiting",
            Post.join_mode != "none",
            deadline_is_open,
            Post.current_members < func.coalesce(Topic.capacity, Post.target_members),
        )
    )
    return session.execute(
        select(
            Topic.id,
            owner.label("is_owner"),
            joined.label("is_joined"),
            pending.label("is_pending"),
            rejected.label("is_rejected"),
            available.label("is_available"),
        ).where(Topic.id.in_(topic_ids))
    ).all()


def _activity_state_from_signals(topic: Topic, signals: Any | None) -> str:
    if topic.participation_mode == "information_only":
        return "closed"
    if signals and signals.is_owner:
        return "owner"
    if signals and signals.is_joined:
        return "joined"
    if signals and signals.is_pending:
        return "pending"
    if signals and signals.is_rejected:
        return "rejected"
    if topic.participation_mode == "open_team":
        return "available"
    if signals and signals.is_available:
        return "available"
    return "closed"


def activity_additive_fields(
    session: Session,
    topic: Topic,
    user_id: int,
    *,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    current = now or _utcnow()
    counts = {
        topic_id: int(count)
        for topic_id, count in _participant_count_rows(session, [topic.id])
    }
    preview = [
        _user_summary(participant)
        for _topic_id, _joined_at, participant in _participant_preview_rows(
            session, [topic.id]
        )
    ]
    signals = _activity_state_rows(
        session,
        [topic.id],
        user_id,
        now=current,
    )
    return {
        "location_name": topic.location_name,
        "campus_scope": topic.campus_scope,
        "capacity": topic.capacity,
        "registration_deadline": _iso(topic.registration_deadline),
        "activity_start_at": _iso(topic.activity_start_at),
        "activity_end_at": _iso(topic.activity_end_at),
        "participant_count": counts.get(topic.id, 0),
        "participant_preview": preview,
        "participation_mode": topic.participation_mode,
        "cover_placeholder_key": activity_placeholder_key(topic),
        "participation_state": _activity_state_from_signals(
            topic, signals[0] if signals else None
        ),
    }


def project_activity_cards(
    session: Session,
    topics: Sequence[Topic],
    user_id: int,
    *,
    now: datetime.datetime | None = None,
) -> list[dict[str, Any]]:
    if not topics:
        return []
    current = now or _utcnow()
    topic_ids = [topic.id for topic in topics]

    tags_by_topic: dict[int, list[dict[str, str]]] = defaultdict(list)
    for topic_id, tag in session.execute(
        select(TopicTag.topic_id, Tag)
        .join(Tag, Tag.id == TopicTag.tag_id)
        .where(TopicTag.topic_id.in_(topic_ids), Tag.active.is_(True))
        .order_by(TopicTag.topic_id, Tag.sort_order, Tag.canonical_name, Tag.id)
    ):
        tags_by_topic[topic_id].append(_tag_projection(tag))

    follow_by_topic = {
        topic_id: (int(count), bool(favorite))
        for topic_id, count, favorite in session.execute(
            select(
                TopicFollow.topic_id,
                func.count(TopicFollow.user_id),
                func.max((TopicFollow.user_id == user_id).cast(Integer)),
            )
            .where(TopicFollow.topic_id.in_(topic_ids))
            .group_by(TopicFollow.topic_id)
        )
    }

    responsible_by_topic: dict[int, list[dict[str, str]]] = defaultdict(list)
    for collaborator, collaborator_user in session.execute(
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
    ):
        responsible_by_topic[collaborator.topic_id].append(
            {
                "user_id": str(collaborator_user.id),
                "nickname": collaborator_user.nickname,
                "role": collaborator.role,
                "badge": "活动负责人",
            }
        )

    organization_ids = {topic.organization_id for topic in topics if topic.organization_id}
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

    participant_counts = {
        topic_id: int(count)
        for topic_id, count in _participant_count_rows(session, topic_ids)
    }
    participants_by_topic: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for topic_id, _joined_at, participant in _participant_preview_rows(
        session, topic_ids
    ):
        participants_by_topic[topic_id].append(_user_summary(participant))

    state_by_topic = {
        row.id: row
        for row in _activity_state_rows(
            session,
            topic_ids,
            user_id,
            now=current,
        )
    }

    projections: list[dict[str, Any]] = []
    for topic in topics:
        follower_count, favorite = follow_by_topic.get(topic.id, (0, False))
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
                "cover_placeholder_key": activity_placeholder_key(topic),
                "location_name": topic.location_name,
                "campus_scope": topic.campus_scope,
                "capacity": topic.capacity,
                "registration_deadline": _iso(topic.registration_deadline),
                "activity_start_at": _iso(topic.activity_start_at),
                "activity_end_at": _iso(topic.activity_end_at),
                "follower_count": follower_count,
                "participant_count": participant_counts.get(topic.id, 0),
                "participant_preview": participants_by_topic[topic.id],
                "participation_mode": topic.participation_mode,
                "favorite": favorite,
                "followed": favorite,
                "participation_state": _activity_state_from_signals(
                    topic, state_by_topic.get(topic.id)
                ),
                "tags": tags_by_topic[topic.id],
                "status": topic.status,
                "trust_badges": trust_badges,
                "responsible_people": responsible_by_topic[topic.id],
            }
        )
    return projections


def _linked_activity(topic: Topic) -> dict[str, Any]:
    return {
        "id": str(topic.id),
        "title": topic.title,
        "short_title": topic.short_title,
        "organizer": topic.organizer,
        "cover_url": topic.cover_url,
        "cover_placeholder_key": activity_placeholder_key(topic),
        "registration_deadline": _iso(topic.registration_deadline),
        "activity_start_at": _iso(topic.activity_start_at),
        "participation_mode": topic.participation_mode,
        "status": topic.status,
    }


def _group_join_state(
    post: Post,
    user_id: int,
    joined_post_ids: set[int],
    applications: dict[int, str],
    topics: dict[int, Topic],
    *,
    now: datetime.datetime,
) -> str:
    if post.topic_id is not None:
        topic = topics.get(post.topic_id)
        if topic is None or topic.status != "active":
            return "closed"
    if post.author_id == user_id:
        return "owner"
    if post.id in joined_post_ids:
        return "joined"
    application_status = applications.get(post.id)
    if application_status in {"pending", "accepted"}:
        return "pending"
    if application_status == "rejected":
        return "rejected"
    if (
        post.join_mode == "none"
        or post.status != "recruiting"
        or deadline_has_passed(post, now=now)
        or post.current_members >= post.target_members
    ):
        return "closed"
    return "available"


def _group_member_preview_rows(
    session: Session, post_ids: Sequence[int]
) -> list[Any]:
    ranked = (
        select(
            Team.post_id.label("post_id"),
            TeamMember.user_id.label("user_id"),
            TeamMember.created_at.label("joined_at"),
            func.row_number()
            .over(
                partition_by=Team.post_id,
                order_by=(TeamMember.created_at, TeamMember.user_id),
            )
            .label("preview_rank"),
        )
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(Team.post_id.in_(post_ids), Team.status == "active")
        .subquery()
    )
    return session.execute(
        select(ranked.c.post_id, ranked.c.joined_at, User)
        .join(User, User.id == ranked.c.user_id)
        .where(ranked.c.preview_rank <= PREVIEW_LIMIT)
        .order_by(ranked.c.post_id, ranked.c.preview_rank)
    ).all()


def _related_group_rows(
    session: Session, topic_ids: Sequence[int]
) -> list[Any]:
    ranked = (
        select(
            Post.id.label("post_id"),
            Post.topic_id.label("topic_id"),
            func.row_number()
            .over(
                partition_by=Post.topic_id,
                order_by=(Post.updated_at.desc(), Post.id.desc()),
            )
            .label("preview_rank"),
        )
        .where(
            Post.topic_id.in_(topic_ids),
            Post.status.in_(PUBLIC_POST_STATUSES),
        )
        .subquery()
    )
    return session.execute(
        select(ranked.c.topic_id, Post)
        .join(Post, Post.id == ranked.c.post_id)
        .where(ranked.c.preview_rank <= RELATED_GROUP_LIMIT)
        .order_by(ranked.c.topic_id, ranked.c.preview_rank)
    ).all()


def project_group_cards(
    session: Session,
    posts: Sequence[Post],
    user_id: int | None,
    *,
    now: datetime.datetime | None = None,
) -> list[dict[str, Any]]:
    if not posts:
        return []
    current = now or _utcnow()
    post_ids = [post.id for post in posts]
    author_ids = {post.author_id for post in posts}
    authors = {
        author.id: author
        for author in session.scalars(select(User).where(User.id.in_(author_ids)))
    }

    tags_by_post: dict[int, list[dict[str, str]]] = defaultdict(list)
    for post_id, tag in session.execute(
        select(PostTag.post_id, Tag)
        .join(Tag, Tag.id == PostTag.tag_id)
        .where(PostTag.post_id.in_(post_ids), Tag.active.is_(True))
        .order_by(PostTag.post_id, Tag.sort_order, Tag.canonical_name, Tag.id)
    ):
        tags_by_post[post_id].append(_tag_projection(tag))

    bookmarked_post_ids = (
        set(
            session.scalars(
                select(PostBookmark.post_id).where(
                    PostBookmark.post_id.in_(post_ids),
                    PostBookmark.user_id == user_id,
                )
            )
        )
        if user_id is not None
        else set()
    )

    members_by_post: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for post_id, _joined_at, member in _group_member_preview_rows(session, post_ids):
        members_by_post[post_id].append(_user_summary(member))

    joined_post_ids = (
        set(
            session.scalars(
                select(Team.post_id)
                .join(TeamMember, TeamMember.team_id == Team.id)
                .where(
                    Team.post_id.in_(post_ids),
                    Team.status == "active",
                    TeamMember.user_id == user_id,
                )
            )
        )
        if user_id is not None
        else set()
    )

    applications: dict[int, str] = {}
    if user_id is not None:
        for application in session.scalars(
            select(Application)
            .where(
                Application.post_id.in_(post_ids),
                Application.applicant_id == user_id,
            )
            .order_by(Application.post_id, Application.created_at.desc(), Application.id.desc())
        ):
            applications.setdefault(application.post_id, application.status)

    topic_ids = {post.topic_id for post in posts if post.topic_id is not None}
    topics = (
        {topic.id: topic for topic in session.scalars(select(Topic).where(Topic.id.in_(topic_ids)))}
        if topic_ids
        else {}
    )

    collaborators_by_post: dict[int, list[dict[str, str]]] = defaultdict(list)
    for collaborator, collaborator_user in session.execute(
        select(PostCollaborator, User)
        .join(User, User.id == PostCollaborator.user_id)
        .where(
            PostCollaborator.post_id.in_(post_ids),
            PostCollaborator.status == "active",
            or_(
                PostCollaborator.expires_at.is_(None),
                PostCollaborator.expires_at > current,
            ),
        )
        .order_by(PostCollaborator.post_id, PostCollaborator.id)
    ):
        collaborators_by_post[collaborator.post_id].append(
            {
                "user_id": str(collaborator_user.id),
                "nickname": collaborator_user.nickname,
                "role": collaborator.role,
                "badge": "帖子协作者",
            }
        )

    projections: list[dict[str, Any]] = []
    for post in posts:
        author = authors.get(post.author_id)
        topic = topics.get(post.topic_id) if post.topic_id is not None else None
        projections.append(
            {
                "id": str(post.id),
                "title": post.title,
                "description": post.description,
                "source_type": post.source_type,
                "kind": post.kind,
                "purpose": post.purpose,
                "join_mode": post.join_mode,
                "topic_id": str(post.topic_id) if post.topic_id is not None else None,
                "main_category": post.main_category,
                "activity_name": post.activity_name,
                "cover_url": post.cover_url,
                "cover_placeholder_key": group_placeholder_key(post),
                "current_members": post.current_members,
                "target_members": post.target_members,
                "needed_roles": post.needed_roles or [],
                "weekly_hours": post.weekly_hours,
                "school_scope": post.school_scope,
                "deadline": post.deadline,
                "risk_level": post.risk_level,
                "status": post.status,
                "author_id": str(post.author_id),
                "author": _user_summary(author) if author else None,
                "bookmark": post.id in bookmarked_post_ids,
                "join_state": (
                    _group_join_state(
                        post,
                        user_id,
                        joined_post_ids,
                        applications,
                        topics,
                        now=current,
                    )
                    if user_id is not None
                    else "closed"
                ),
                "member_preview": members_by_post[post.id],
                "linked_activity": (
                    _linked_activity(topic) if topic and topic.status == "active" else None
                ),
                "tags": tags_by_post[post.id],
                "collaborators": collaborators_by_post[post.id],
                "created_at": _iso(post.created_at),
            }
        )
    return projections


def _activity_query(
    *,
    q: str = "",
    tag_ids: Sequence[str] | str | None = None,
    date_filter: str = "",
    status: str = "active",
    type_filter: str = "",
    campus: str = "",
    now: datetime.datetime,
):
    statement = select(Topic).where(
        Topic.status == "active",
        Topic.channel.in_(FORMAL_ACTIVITY_CHANNELS),
    )
    query_text = q.strip()
    if query_text:
        pattern = f"%{query_text}%"
        statement = statement.where(
            or_(
                Topic.title.ilike(pattern),
                Topic.short_title.ilike(pattern),
                Topic.organizer.ilike(pattern),
                Topic.summary.ilike(pattern),
            )
        )
    for tag_id in _selected_tags(tag_ids):
        statement = statement.where(
            exists(
                select(TopicTag.topic_id)
                .join(Tag, Tag.id == TopicTag.tag_id)
                .where(
                    TopicTag.topic_id == Topic.id,
                    TopicTag.tag_id == tag_id,
                    Tag.active.is_(True),
                )
            )
        )
    if status in {"registration_open", "open"}:
        statement = statement.where(
            or_(Topic.registration_deadline.is_(None), Topic.registration_deadline >= now)
        )
    elif status in {"ended", "past"}:
        statement = statement.where(Topic.activity_end_at < now)
    if type_filter:
        statement = statement.where(
            or_(Topic.channel == type_filter, Topic.participation_mode == type_filter)
        )
    if campus.strip():
        statement = statement.where(Topic.campus_scope == campus.strip())
    if date_filter == "upcoming":
        statement = statement.where(
            or_(Topic.activity_end_at.is_(None), Topic.activity_end_at >= now)
        )
    elif date_filter in {"registration_open", "open"}:
        statement = statement.where(
            or_(Topic.registration_deadline.is_(None), Topic.registration_deadline >= now)
        )
    elif date_filter in {"past", "ended"}:
        statement = statement.where(Topic.activity_end_at < now)
    return statement


def list_activities(
    session: Session,
    user_id: int,
    *,
    q: str = "",
    tag_ids: Sequence[str] | str | None = None,
    date_filter: str = "",
    status: str = "active",
    type_filter: str = "",
    campus: str = "",
    page: int = 1,
    page_size: int = 20,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    current = now or _utcnow()
    page, page_size = _pagination(page, page_size)
    statement = _activity_query(
        q=q,
        tag_ids=tag_ids,
        date_filter=date_filter,
        status=status,
        type_filter=type_filter,
        campus=campus,
        now=current,
    )
    total = int(session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    topics = list(
        session.scalars(
            statement.order_by(Topic.updated_at.desc(), Topic.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return _page(project_activity_cards(session, topics, user_id, now=current), total, page, page_size)


def get_activity_detail(
    session: Session,
    topic_id: int,
    user_id: int,
    *,
    now: datetime.datetime | None = None,
) -> dict[str, Any] | None:
    current = now or _utcnow()
    topic = session.scalar(
        select(Topic).where(
            Topic.id == topic_id,
            Topic.status == "active",
            Topic.channel.in_(FORMAL_ACTIVITY_CHANNELS),
        )
    )
    if topic is None:
        return None
    detail = project_activity_cards(session, [topic], user_id, now=current)[0]
    related_posts = [post for _topic_id, post in _related_group_rows(session, [topic.id])]
    detail["related_groups"] = project_group_cards(
        session, related_posts, user_id, now=current
    )
    return detail


def _group_query(
    *,
    q: str = "",
    tag_ids: Sequence[str] | str | None = None,
    date_filter: str = "",
    status: str = "",
    type_filter: str = "",
    campus: str = "",
    now: datetime.datetime,
    dialect_name: str = "sqlite",
):
    statement = select(Post).where(Post.status.in_(PUBLIC_POST_STATUSES))
    query_text = q.strip()
    if query_text:
        pattern = f"%{query_text}%"
        statement = statement.where(
            or_(
                Post.title.ilike(pattern),
                Post.description.ilike(pattern),
                Post.activity_name.ilike(pattern),
            )
        )
    for tag_id in _selected_tags(tag_ids):
        statement = statement.where(
            exists(
                select(PostTag.post_id)
                .join(Tag, Tag.id == PostTag.tag_id)
                .where(
                    PostTag.post_id == Post.id,
                    PostTag.tag_id == tag_id,
                    Tag.active.is_(True),
                )
            )
        )
    if status:
        resolved_status = "recruiting" if status == "open" else status
        statement = statement.where(Post.status == resolved_status)
    if type_filter:
        statement = statement.where(
            or_(Post.purpose == type_filter, Post.kind == type_filter)
        )
    if campus.strip():
        statement = statement.where(Post.school_scope == campus.strip())
    deadline_predicate = _deadline_range_predicate(date_filter, now, dialect_name)
    if deadline_predicate is not None:
        statement = statement.where(deadline_predicate)
    return statement


def list_groups(
    session: Session,
    user_id: int,
    *,
    q: str = "",
    tag_ids: Sequence[str] | str | None = None,
    date_filter: str = "",
    status: str = "",
    type_filter: str = "",
    campus: str = "",
    page: int = 1,
    page_size: int = 20,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    current = now or _utcnow()
    page, page_size = _pagination(page, page_size)
    statement = _group_query(
        q=q,
        tag_ids=tag_ids,
        date_filter=date_filter,
        status=status,
        type_filter=type_filter,
        campus=campus,
        now=current,
        dialect_name=session.get_bind().dialect.name,
    )
    total = int(session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    posts = list(
        session.scalars(
            statement.order_by(Post.updated_at.desc(), Post.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return _page(project_group_cards(session, posts, user_id, now=current), total, page, page_size)


def get_group_detail(
    session: Session,
    post_id: int,
    user_id: int,
    *,
    now: datetime.datetime | None = None,
) -> dict[str, Any] | None:
    post = session.scalar(
        select(Post).where(Post.id == post_id, Post.status.in_(PUBLIC_POST_STATUSES))
    )
    if post is None:
        return None
    return project_group_cards(session, [post], user_id, now=now)[0]
