from __future__ import annotations

import datetime
import math
from typing import Any, Literal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from services.collaboration_lifecycle import PUBLIC_POST_STATUSES
from services.explore import project_activity_cards, project_group_cards
from services.onboarding import normalized_profile_visibility
from storage.database.models import (
    Application,
    Post,
    PostBookmark,
    Team,
    TeamMember,
    Topic,
    TopicFollow,
    User,
)


ActivityView = Literal["attending", "saved", "past"]
GroupView = Literal["joined", "pending", "saved", "archived"]
PUBLIC_PREVIEW_LIMIT = 8


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _page(
    items: list[dict[str, Any]], total: int, page: int, page_size: int
) -> dict[str, Any]:
    return {
        "list": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


def _activity_participations(user_id: int, *, active_teams_only: bool):
    statement = (
        select(
            Post.topic_id.label("topic_id"),
            func.max(TeamMember.created_at).label("relation_at"),
        )
        .join(Team, Team.post_id == Post.id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user_id, Post.topic_id.is_not(None))
    )
    if active_teams_only:
        statement = statement.where(Team.status == "active")
    return statement.group_by(Post.topic_id).subquery()


def list_personal_activities(
    session: Session,
    user_id: int,
    *,
    view: ActivityView,
    page: int,
    page_size: int,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    current = now or utcnow()
    effective_end = func.coalesce(
        Topic.activity_end_at,
        Topic.activity_start_at,
        Topic.registration_deadline,
    )
    if view == "saved":
        base = (
            select(Topic, TopicFollow.created_at.label("relation_at"))
            .join(TopicFollow, TopicFollow.topic_id == Topic.id)
            .where(TopicFollow.user_id == user_id, Topic.status == "active")
        )
        order = (TopicFollow.created_at.desc(), Topic.id.desc())
    else:
        participations = _activity_participations(
            user_id, active_teams_only=view == "attending"
        )
        base = (
            select(Topic, participations.c.relation_at)
            .join(participations, participations.c.topic_id == Topic.id)
            .where(Topic.status == "active")
        )
        if view == "attending":
            base = base.where(effective_end >= current)
            order = (effective_end.asc(), Topic.id.desc())
        else:
            base = base.where(effective_end < current)
            order = (effective_end.desc(), Topic.id.desc())

    total = int(
        session.scalar(
            select(func.count()).select_from(
                base.with_only_columns(Topic.id).subquery()
            )
        )
        or 0
    )
    rows = session.execute(
        base.order_by(*order).offset((page - 1) * page_size).limit(page_size)
    ).all()
    topics = [row[0] for row in rows]
    return _page(
        project_activity_cards(session, topics, user_id, now=current),
        total,
        page,
        page_size,
    )


def _group_base(user_id: int, view: GroupView):
    if view in {"joined", "archived"}:
        base = (
            select(Post, func.coalesce(TeamMember.created_at, Post.created_at).label("relation_at"))
            .outerjoin(Team, Team.post_id == Post.id)
            .outerjoin(
                TeamMember,
                and_(TeamMember.team_id == Team.id, TeamMember.user_id == user_id),
            )
            .where(
                or_(TeamMember.user_id == user_id, Post.author_id == user_id),
                Post.status.in_(PUBLIC_POST_STATUSES),
            )
        )
        if view == "joined":
            base = base.where(
                or_(Team.status == "active", Team.id.is_(None)),
                Post.archived_at.is_(None),
                Post.deleted_at.is_(None),
            )
        else:
            base = base.where(
                or_(
                    Team.status != "active",
                    Post.archived_at.is_not(None),
                    Post.deleted_at.is_not(None),
                )
            )
        return base, TeamMember.created_at.desc()
    if view == "pending":
        return (
            select(Post, Application.created_at.label("relation_at"))
            .join(Application, Application.post_id == Post.id)
            .where(
                Application.applicant_id == user_id,
                Application.status == "pending",
                Post.status.in_(PUBLIC_POST_STATUSES),
            ),
            Application.created_at.desc(),
        )
    return (
        select(Post, PostBookmark.created_at.label("relation_at"))
        .join(PostBookmark, PostBookmark.post_id == Post.id)
        .where(
            PostBookmark.user_id == user_id,
            Post.status.in_(PUBLIC_POST_STATUSES),
        ),
        PostBookmark.created_at.desc(),
    )


def list_personal_groups(
    session: Session,
    user_id: int,
    *,
    view: GroupView,
    page: int,
    page_size: int,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    current = now or utcnow()
    base, relation_order = _group_base(user_id, view)
    total = int(
        session.scalar(
            select(func.count()).select_from(
                base.with_only_columns(Post.id).subquery()
            )
        )
        or 0
    )
    rows = session.execute(
        base.order_by(relation_order, Post.updated_at.desc(), Post.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    posts = [row[0] for row in rows]
    return _page(
        project_group_cards(session, posts, user_id, now=current),
        total,
        page,
        page_size,
    )


def public_profile(
    session: Session,
    user: User,
    viewer_id: int,
    *,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    owner = user.id == viewer_id
    visibility = normalized_profile_visibility(user.profile_visibility)
    data: dict[str, Any] = {
        "id": str(user.id),
        "nickname": user.nickname,
        "avatar": user.avatar,
        "bio": user.bio,
        "looking_for": user.looking_for or [],
        "is_owner": owner,
    }
    for field in ("major", "grade", "interests", "skills", "availability"):
        if owner or visibility[field]:
            value = getattr(user, field)
            if value is not None:
                data[field] = value
    if owner or visibility["contact"]:
        contact = {"wechat": user.wechat} if user.wechat else {}
        if contact:
            data["contact"] = contact
    if owner or visibility["activities"]:
        activities = list_personal_activities(
            session,
            user.id,
            view="attending",
            page=1,
            page_size=PUBLIC_PREVIEW_LIMIT,
            now=now,
        )["list"]
        if not owner:
            _redact_embedded_profile_fields(activities, user.id, visibility)
        data["activities"] = activities
    if owner or visibility["groups"]:
        groups = list_personal_groups(
            session,
            user.id,
            view="joined",
            page=1,
            page_size=PUBLIC_PREVIEW_LIMIT,
            now=now,
        )["list"]
        if not owner:
            _redact_embedded_profile_fields(groups, user.id, visibility)
        data["groups"] = groups
    return data


def _redact_embedded_profile_fields(
    cards: list[dict[str, Any]],
    profile_user_id: int,
    visibility: dict[str, bool],
) -> None:
    for card in cards:
        summaries = [
            *card.get("participant_preview", []),
            *card.get("member_preview", []),
        ]
        author = card.get("author")
        if isinstance(author, dict):
            summaries.append(author)
        for summary in summaries:
            if (
                not isinstance(summary, dict)
                or summary.get("id") != str(profile_user_id)
            ):
                continue
            for field in ("major", "grade"):
                if not visibility[field]:
                    summary.pop(field, None)
