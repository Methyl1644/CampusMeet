from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Literal, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.collaboration_lifecycle import deadline_has_passed
from services.permissions import can_manage_topic
from storage.database.models import Application, Post, Team, TeamMember, Topic, User


class ParticipationMode(StrEnum):
    OPEN_TEAM = "open_team"
    OFFICIAL_SIGNUP = "official_signup"
    INFORMATION_ONLY = "information_only"


class PostPurpose(StrEnum):
    TEAM_RECRUITMENT = "team_recruitment"
    OFFICIAL_SIGNUP = "official_signup"
    DISCUSSION = "discussion"


class JoinMode(StrEnum):
    APPLICATION = "application"
    DIRECT = "direct"
    NONE = "none"


PARTICIPATION_MODES = frozenset(ParticipationMode)
POST_PURPOSES = frozenset(PostPurpose)
JOIN_MODES = frozenset(JoinMode)

PURPOSE_JOIN_MODES = MappingProxyType(
    {
        PostPurpose.TEAM_RECRUITMENT: JoinMode.APPLICATION,
        PostPurpose.OFFICIAL_SIGNUP: JoinMode.DIRECT,
        PostPurpose.DISCUSSION: JoinMode.NONE,
    }
)

ALLOWED_PURPOSES = MappingProxyType(
    {
        ParticipationMode.OPEN_TEAM: frozenset(
            {PostPurpose.TEAM_RECRUITMENT, PostPurpose.DISCUSSION}
        ),
        ParticipationMode.OFFICIAL_SIGNUP: frozenset(
            {PostPurpose.OFFICIAL_SIGNUP, PostPurpose.DISCUSSION}
        ),
        ParticipationMode.INFORMATION_ONLY: frozenset({PostPurpose.DISCUSSION}),
    }
)

ERROR_MESSAGES = MappingProxyType(
    {
        "participation.forbidden_purpose": "该活动不允许发布此用途的帖子",
        "participation.official_signup_forbidden": "只有活动管理者可以发布官方报名帖",
        "participation.duplicate_official_signup": "该活动已有有效的官方报名帖",
        "participation.closed": "该帖子已停止参与或已过截止时间",
        "participation.full": "活动名额已满",
        "participation.invalid_join_mode": "帖子加入方式与用途不匹配",
    }
)

JoinState = Literal["owner", "joined", "pending", "rejected", "available", "closed"]


class ParticipationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        self.message = ERROR_MESSAGES[code]
        super().__init__(self.message)


@dataclass(frozen=True)
class ParticipationDecision:
    participation_mode: ParticipationMode
    purpose: PostPurpose
    join_mode: JoinMode
    topic: Topic | None


def _enum_value(enum_type, value: Any, error_code: str):
    try:
        return enum_type(str(value))
    except ValueError as exc:
        raise ParticipationError(error_code) from exc


def _topic_for_payload(
    session: Session,
    payload: Mapping[str, Any],
    existing: Post | None,
) -> Topic | None:
    raw_topic_id = payload.get("topic_id", existing.topic_id if existing is not None else None)
    if raw_topic_id in {None, ""}:
        return None
    try:
        topic_id = int(raw_topic_id)
    except (TypeError, ValueError) as exc:
        raise ParticipationError("participation.forbidden_purpose") from exc
    topic = session.get(Topic, topic_id)
    if topic is None or topic.status != "active":
        raise ParticipationError("participation.closed")
    return topic


def _resolved_purpose(payload: Mapping[str, Any], existing: Post | None) -> PostPurpose:
    raw = payload.get(
        "purpose",
        existing.purpose if existing is not None else PostPurpose.TEAM_RECRUITMENT,
    )
    return _enum_value(PostPurpose, raw, "participation.forbidden_purpose")


def _resolved_join_mode(
    payload: Mapping[str, Any],
    existing: Post | None,
    purpose: PostPurpose,
) -> JoinMode:
    purpose_changed = "purpose" in payload and (
        existing is None or str(existing.purpose) != str(purpose)
    )
    if "join_mode" in payload:
        raw = payload["join_mode"]
    elif existing is not None and not purpose_changed:
        raw = existing.join_mode
    else:
        raw = PURPOSE_JOIN_MODES[purpose]
    join_mode = _enum_value(JoinMode, raw, "participation.invalid_join_mode")
    if join_mode != PURPOSE_JOIN_MODES[purpose]:
        raise ParticipationError("participation.invalid_join_mode")
    return join_mode


def _official_signup_exists(
    session: Session,
    topic_id: int,
    existing: Post | None,
) -> bool:
    query = select(Post.id).where(
        Post.topic_id == topic_id,
        Post.purpose == PostPurpose.OFFICIAL_SIGNUP,
        Post.status.in_(("recruiting", "full")),
    )
    if existing is not None and existing.id is not None:
        query = query.where(Post.id != existing.id)
    return session.scalar(query.limit(1)) is not None


def validate_post_participation(
    session: Session,
    user: User,
    payload: Mapping[str, Any],
    *,
    existing: Post | None = None,
) -> ParticipationDecision:
    topic = _topic_for_payload(session, payload, existing)
    purpose = _resolved_purpose(payload, existing)
    join_mode = _resolved_join_mode(payload, existing, purpose)
    participation_mode = (
        _enum_value(
            ParticipationMode,
            topic.participation_mode,
            "participation.forbidden_purpose",
        )
        if topic is not None
        else ParticipationMode.OPEN_TEAM
    )

    if purpose not in ALLOWED_PURPOSES[participation_mode]:
        raise ParticipationError("participation.forbidden_purpose")

    effective_status = str(
        payload.get("status", existing.status if existing is not None else "recruiting")
    )
    if purpose == PostPurpose.OFFICIAL_SIGNUP:
        if topic is None:
            raise ParticipationError("participation.forbidden_purpose")
        becoming_official = existing is None or existing.purpose != PostPurpose.OFFICIAL_SIGNUP
        if becoming_official and not can_manage_topic(session, user, topic, "edit_topic"):
            raise ParticipationError("participation.official_signup_forbidden")
        if effective_status in {"recruiting", "full"} and _official_signup_exists(
            session,
            topic.id,
            existing,
        ):
            raise ParticipationError("participation.duplicate_official_signup")

    return ParticipationDecision(
        participation_mode=participation_mode,
        purpose=purpose,
        join_mode=join_mode,
        topic=topic,
    )


def _participation_capacity(session: Session, post: Post) -> int:
    if post.topic_id is not None and post.purpose == PostPurpose.OFFICIAL_SIGNUP:
        topic = session.get(Topic, post.topic_id)
        if topic is not None and topic.capacity is not None:
            return topic.capacity
    return post.target_members


def _locked_team(session: Session, post_id: int) -> Team | None:
    return session.scalar(
        select(Team).where(Team.post_id == post_id).with_for_update()
    )


def _membership(session: Session, team_id: int, user_id: int) -> TeamMember | None:
    return session.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )


def _add_membership(
    session: Session,
    team: Team,
    user: User,
    *,
    member_role: str,
) -> TeamMember:
    membership = TeamMember(
        team_id=team.id,
        user_id=user.id,
        suggested_role="",
        member_role=member_role,
    )
    session.add(membership)
    user.team_count = (user.team_count or 0) + 1
    session.flush()
    return membership


def join_post_directly(session: Session, post: Post, user: User) -> TeamMember:
    if post.id is None:
        session.flush()
    locked_post = session.scalar(
        select(Post).where(Post.id == post.id).with_for_update()
    )
    if locked_post is None:
        raise ParticipationError("participation.closed")
    decision = validate_post_participation(
        session,
        user,
        {},
        existing=locked_post,
    )
    if decision.join_mode != JoinMode.DIRECT:
        raise ParticipationError("participation.invalid_join_mode")

    team = _locked_team(session, locked_post.id)
    if team is not None:
        existing_membership = _membership(session, team.id, user.id)
        if existing_membership is not None:
            return existing_membership

    if locked_post.status == "full":
        raise ParticipationError("participation.full")
    if locked_post.status != "recruiting" or deadline_has_passed(locked_post):
        raise ParticipationError("participation.closed")

    capacity = _participation_capacity(session, locked_post)
    if team is None:
        prospective_members = 1 if user.id == locked_post.author_id else 2
        if prospective_members > capacity:
            raise ParticipationError("participation.full")
        team = Team(
            post_id=locked_post.id,
            owner_id=locked_post.author_id,
            activity_name=locked_post.activity_name,
            division_of_labor=[],
            meeting_agenda=[],
            task_list=[],
            risk_reminders=[],
            contact_info=[],
        )
        session.add(team)
        session.flush()
        owner = session.get(User, locked_post.author_id)
        if owner is None:
            raise ParticipationError("participation.closed")
        owner_membership = _add_membership(
            session,
            team,
            owner,
            member_role="owner",
        )
        if user.id == owner.id:
            locked_post.current_members = 1
            locked_post.status = "full" if capacity == 1 else "recruiting"
            return owner_membership

    member_count = int(
        session.scalar(
            select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team.id)
        )
        or 0
    )
    if member_count >= capacity:
        locked_post.current_members = member_count
        locked_post.status = "full"
        raise ParticipationError("participation.full")

    membership = _add_membership(session, team, user, member_role="member")
    member_count += 1
    locked_post.current_members = member_count
    locked_post.status = "full" if member_count >= capacity else "recruiting"
    return membership


def validate_application_join(session: Session, post: Post, user: User) -> None:
    if get_join_state(session, post, user.id) == "joined":
        return
    decision = validate_post_participation(
        session,
        user,
        {},
        existing=post,
    )
    if decision.join_mode != JoinMode.APPLICATION:
        raise ParticipationError("participation.invalid_join_mode")
    if post.status == "full" or post.current_members >= _participation_capacity(session, post):
        raise ParticipationError("participation.full")
    if post.status != "recruiting" or deadline_has_passed(post):
        raise ParticipationError("participation.closed")


def get_join_state(session: Session, post: Post, user_id: int) -> JoinState:
    if post.author_id == user_id:
        return "owner"

    membership = session.scalar(
        select(TeamMember)
        .join(Team, TeamMember.team_id == Team.id)
        .where(Team.post_id == post.id, TeamMember.user_id == user_id)
        .limit(1)
    )
    if membership is not None:
        return "joined"

    application = session.scalar(
        select(Application)
        .where(Application.post_id == post.id, Application.applicant_id == user_id)
        .order_by(Application.created_at.desc(), Application.id.desc())
        .limit(1)
    )
    if application is not None and application.status in {"pending", "accepted"}:
        return "pending"
    if application is not None and application.status == "rejected":
        return "rejected"

    if post.join_mode == JoinMode.NONE:
        return "closed"
    if post.status != "recruiting" or deadline_has_passed(post):
        return "closed"
    if post.current_members >= _participation_capacity(session, post):
        return "closed"
    return "available"
