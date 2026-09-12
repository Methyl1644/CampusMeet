from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Literal, Mapping

from sqlalchemy import case, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.permissions import can_manage_post, can_manage_topic
from storage.database.models import (
    Application,
    AuditLog,
    Conversation,
    Post,
    Team,
    TeamMember,
    Topic,
    User,
)


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

EFFECTIVE_POST_STATUSES = frozenset({"recruiting", "full"})
OFFICIAL_SIGNUP_UNIQUE_INDEX = "uq_posts_effective_official_signup_topic"
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


@dataclass(frozen=True)
class TeamConfirmationResult:
    conversation: Conversation
    post: Post | None
    team: Team | None
    waiting_for_other: bool


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def deadline_has_passed(post: Post, *, now: datetime.datetime | None = None) -> bool:
    raw = str(post.deadline or "").strip()
    if not raw:
        return False
    try:
        parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed_date = datetime.date.fromisoformat(raw)
        except ValueError:
            return False
        parsed = datetime.datetime.combine(
            parsed_date,
            datetime.time.max,
            tzinfo=datetime.timezone.utc,
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed <= (now or utcnow())


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
        Post.status.in_(EFFECTIVE_POST_STATUSES),
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
        if effective_status in EFFECTIVE_POST_STATUSES and _official_signup_exists(
            session,
            topic.id,
            existing,
        ):
            raise ParticipationError("participation.duplicate_official_signup")

    return ParticipationDecision(participation_mode, purpose, join_mode, topic)


def _post_write_snapshot(post: Post) -> tuple[int | None, str, str, int | None]:
    return post.topic_id, str(post.purpose), str(post.status), post.id


def _translate_post_integrity_error(
    session: Session,
    snapshot: tuple[int | None, str, str, int | None],
    error: IntegrityError,
) -> None:
    topic_id, purpose, status, post_id = snapshot
    diagnostic = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    session.rollback()
    if constraint_name == OFFICIAL_SIGNUP_UNIQUE_INDEX:
        raise ParticipationError("participation.duplicate_official_signup") from None
    if (
        topic_id is not None
        and purpose == PostPurpose.OFFICIAL_SIGNUP
        and status in EFFECTIVE_POST_STATUSES
    ):
        query = select(Post.id).where(
            Post.topic_id == topic_id,
            Post.purpose == PostPurpose.OFFICIAL_SIGNUP,
            Post.status.in_(EFFECTIVE_POST_STATUSES),
        )
        if post_id is not None:
            query = query.where(Post.id != post_id)
        if session.scalar(query.limit(1)) is not None:
            raise ParticipationError("participation.duplicate_official_signup") from None
    raise error


def flush_post_participation(session: Session, post: Post) -> None:
    snapshot = _post_write_snapshot(post)
    try:
        session.flush()
    except IntegrityError as exc:
        _translate_post_integrity_error(session, snapshot, exc)


def commit_post_participation(session: Session, post: Post) -> None:
    snapshot = _post_write_snapshot(post)
    try:
        session.commit()
    except IntegrityError as exc:
        _translate_post_integrity_error(session, snapshot, exc)


def _participation_capacity(session: Session, post: Post) -> int:
    if post.topic_id is not None and post.purpose == PostPurpose.OFFICIAL_SIGNUP:
        topic = session.get(Topic, post.topic_id)
        if topic is not None and topic.capacity is not None:
            return topic.capacity
    return post.target_members


def _locked_post(session: Session, post_id: int) -> Post | None:
    return session.scalar(select(Post).where(Post.id == post_id).with_for_update())


def _locked_team(session: Session, post_id: int) -> Team | None:
    return session.scalar(select(Team).where(Team.post_id == post_id).with_for_update())


def _membership(session: Session, team_id: int, user_id: int) -> TeamMember | None:
    return session.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
    )


def _increment_team_count(session: Session, user: User) -> None:
    session.execute(
        update(User)
        .where(User.id == user.id)
        .values(team_count=func.coalesce(User.team_count, 0) + 1)
        .execution_options(synchronize_session=False)
    )
    session.expire(user, ["team_count"])


def _ensure_membership(
    session: Session,
    team: Team,
    user: User,
    *,
    member_role: str,
    suggested_role: str = "",
) -> tuple[TeamMember, bool]:
    existing = _membership(session, team.id, user.id)
    if existing is not None:
        return existing, False
    membership = TeamMember(
        team_id=team.id,
        user_id=user.id,
        suggested_role=suggested_role,
        member_role=member_role,
    )
    try:
        with session.begin_nested():
            session.add(membership)
            session.flush()
    except IntegrityError:
        existing = _membership(session, team.id, user.id)
        if existing is None:
            raise
        return existing, False
    _increment_team_count(session, user)
    return membership, True


def _create_or_find_team(session: Session, post: Post, owner: User) -> Team:
    team = _locked_team(session, post.id)
    if team is not None:
        if team.owner_id is None:
            team.owner_id = owner.id
        return team
    team = Team(
        post_id=post.id,
        owner_id=owner.id,
        activity_name=post.activity_name,
        division_of_labor=[],
        meeting_agenda=[],
        task_list=[],
        risk_reminders=[],
        contact_info=[],
    )
    try:
        with session.begin_nested():
            session.add(team)
            session.flush()
    except IntegrityError:
        team = _locked_team(session, post.id)
        if team is None:
            raise
    return team


def _topic_is_open(session: Session, post: Post) -> bool:
    if post.topic_id is None:
        return True
    topic = session.get(Topic, post.topic_id)
    return topic is not None and topic.status == "active"


def set_post_status(
    session: Session,
    post: Post,
    status: str,
    *,
    actor: User | None = None,
) -> Post:
    if status in EFFECTIVE_POST_STATUSES:
        policy_actor = actor or session.get(User, post.author_id)
        if policy_actor is None:
            raise ParticipationError("participation.closed")
        validate_post_participation(
            session,
            policy_actor,
            {"status": status},
            existing=post,
        )
    post.status = status
    return post


def _member_count(session: Session, team_id: int) -> int:
    return int(
        session.scalar(
            select(func.count(func.distinct(TeamMember.user_id))).where(
                TeamMember.team_id == team_id
            )
        )
        or 0
    )


def synchronize_post_membership(session: Session, post: Post, team: Team) -> int:
    count = _member_count(session, team.id)
    post.current_members = count
    if post.status in EFFECTIVE_POST_STATUSES:
        capacity = _participation_capacity(session, post)
        if count >= capacity:
            target_status = "full"
        elif deadline_has_passed(post) or not _topic_is_open(session, post):
            target_status = "closed"
        else:
            target_status = "recruiting"
        set_post_status(session, post, target_status)
    return count


def _reserve_capacity(session: Session, post: Post, capacity: int) -> None:
    result = session.execute(
        update(Post)
        .where(
            Post.id == post.id,
            Post.status == "recruiting",
            Post.current_members < capacity,
        )
        .values(
            current_members=Post.current_members + 1,
            status=case(
                (Post.current_members + 1 >= capacity, "full"),
                else_="recruiting",
            ),
        )
        .execution_options(synchronize_session=False)
    )
    session.expire(post, ["current_members", "status"])
    if int(result.rowcount or 0) == 1:
        return
    if post.status == "full" or post.current_members >= capacity:
        raise ParticipationError("participation.full")
    raise ParticipationError("participation.closed")


def _prepare_team(session: Session, post: Post) -> tuple[Team, User]:
    owner = session.get(User, post.author_id)
    if owner is None:
        raise ParticipationError("participation.closed")
    team = _create_or_find_team(session, post, owner)
    _ensure_membership(session, team, owner, member_role="owner")
    synchronize_post_membership(session, post, team)
    return team, owner


def _admit_member(
    session: Session,
    post: Post,
    team: Team,
    user: User,
    *,
    suggested_role: str = "",
) -> TeamMember:
    existing = _membership(session, team.id, user.id)
    if existing is not None:
        synchronize_post_membership(session, post, team)
        return existing
    _reserve_capacity(session, post, _participation_capacity(session, post))
    membership, _ = _ensure_membership(
        session,
        team,
        user,
        member_role="member",
        suggested_role=suggested_role,
    )
    synchronize_post_membership(session, post, team)
    return membership


def join_post_directly(session: Session, post: Post, user: User) -> TeamMember:
    if post.id is None:
        session.flush()
    locked_post = _locked_post(session, post.id)
    if locked_post is None:
        raise ParticipationError("participation.closed")
    decision = validate_post_participation(session, user, {}, existing=locked_post)
    if decision.join_mode != JoinMode.DIRECT:
        raise ParticipationError("participation.invalid_join_mode")
    team = _locked_team(session, locked_post.id)
    if team is not None:
        existing = _membership(session, team.id, user.id)
        if existing is not None:
            return existing
    if locked_post.status not in EFFECTIVE_POST_STATUSES or deadline_has_passed(locked_post):
        raise ParticipationError("participation.closed")
    team, owner = _prepare_team(session, locked_post)
    if user.id == owner.id:
        membership = _membership(session, team.id, user.id)
        if membership is None:
            raise ParticipationError("participation.closed")
        return membership
    if locked_post.status == "full":
        raise ParticipationError("participation.full")
    return _admit_member(session, locked_post, team, user)


def validate_application_join(session: Session, post: Post, user: User) -> None:
    if get_join_state(session, post, user.id) == "joined":
        return
    decision = validate_post_participation(session, user, {}, existing=post)
    if decision.join_mode != JoinMode.APPLICATION:
        raise ParticipationError("participation.invalid_join_mode")
    if post.status == "full" or post.current_members >= _participation_capacity(session, post):
        raise ParticipationError("participation.full")
    if post.status != "recruiting" or deadline_has_passed(post):
        raise ParticipationError("participation.closed")


def _begin_confirmation_transaction(session: Session) -> None:
    if session.get_bind().dialect.name == "sqlite" and not session.in_transaction():
        session.execute(text("BEGIN IMMEDIATE"))


def _locked_conversation(session: Session, conversation_id: int) -> Conversation | None:
    return session.scalar(
        select(Conversation).where(Conversation.id == conversation_id).with_for_update()
    )


def _contact_item(user: User) -> dict[str, str | None]:
    return {
        "user_id": str(user.id),
        "nickname": user.nickname,
        "phone": user.phone,
        "wechat": user.wechat,
    }


def _unlock_team_contacts(team: Team, users: tuple[User, User]) -> None:
    contacts = list(team.contact_info or [])
    contact_ids = {str(item.get("user_id")) for item in contacts}
    for user in users:
        if str(user.id) not in contact_ids:
            contacts.append(_contact_item(user))
            contact_ids.add(str(user.id))
    team.contact_info = contacts


def confirm_team_participation(
    session: Session,
    conversation_id: int,
    user_id: int,
) -> TeamConfirmationResult:
    _begin_confirmation_transaction(session)
    conversation = _locked_conversation(session, conversation_id)
    if conversation is None:
        raise ValueError("会话不存在")
    if user_id not in {conversation.post_author_id, conversation.applicant_id}:
        raise PermissionError("无权操作")
    if conversation.status == "closed":
        raise ValueError("会话已关闭")
    if user_id == conversation.post_author_id:
        conversation.author_confirmed = True
    else:
        conversation.applicant_confirmed = True
    if not (conversation.author_confirmed and conversation.applicant_confirmed):
        return TeamConfirmationResult(conversation, None, None, True)

    post = _locked_post(session, conversation.post_id)
    author = session.get(User, conversation.post_author_id)
    applicant = session.get(User, conversation.applicant_id)
    if post is None:
        raise ValueError("帖子不存在")
    if author is None or applicant is None:
        raise ValueError("用户信息不完整")
    decision = validate_post_participation(session, applicant, {}, existing=post)
    if decision.join_mode != JoinMode.APPLICATION:
        raise ParticipationError("participation.invalid_join_mode")
    if post.status not in EFFECTIVE_POST_STATUSES or deadline_has_passed(post):
        raise ParticipationError("participation.closed")

    team, _ = _prepare_team(session, post)
    existing = _membership(session, team.id, applicant.id)
    if existing is None:
        if post.status == "full":
            raise ParticipationError("participation.full")
        role = ""
        if conversation.application_id is not None:
            application = session.get(Application, conversation.application_id)
            role = application.role_wanted if application is not None else ""
        _admit_member(session, post, team, applicant, suggested_role=role)
    else:
        synchronize_post_membership(session, post, team)

    _unlock_team_contacts(team, (author, applicant))
    conversation.status = "team_confirmed"
    conversation.contact_unlocked = True
    return TeamConfirmationResult(conversation, post, team, False)


def transition_post_status(session: Session, actor: User, post: Post, action: str) -> Post:
    if not can_manage_post(session, actor, post, "update_status"):
        raise PermissionError("你没有更新该帖子状态的权限")
    now = utcnow()
    if action == "close":
        if post.status in {"archived", "deleted"}:
            raise ValueError("当前帖子不能关闭")
        set_post_status(session, post, "closed", actor=actor)
        post.closed_at = now
    elif action == "reopen":
        if post.status in {"archived", "deleted"}:
            raise ValueError("归档或删除的帖子不能重新招募")
        if deadline_has_passed(post, now=now):
            raise ValueError("招募已过截止时间")
        target = "full" if post.current_members >= _participation_capacity(session, post) else "recruiting"
        set_post_status(session, post, target, actor=actor)
    elif action == "archive":
        if post.status == "deleted":
            raise ValueError("已删除的帖子不能归档")
        set_post_status(session, post, "archived", actor=actor)
        post.archived_at = now
    elif action == "delete":
        set_post_status(session, post, "deleted", actor=actor)
        post.deleted_at = now
    else:
        raise ValueError("帖子状态操作不受支持")
    session.add(
        AuditLog(
            user_id=actor.id,
            action=f"post.{action}",
            target_type="post",
            target_id=str(post.id),
            detail=json.dumps({"status": post.status}, ensure_ascii=False),
        )
    )
    return post


def get_join_state(session: Session, post: Post, user_id: int) -> JoinState:
    if not _topic_is_open(session, post):
        return "closed"
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
