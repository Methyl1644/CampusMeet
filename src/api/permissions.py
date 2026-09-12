import datetime
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from api.common import api_ok, current_user_id
from api.schemas.content import CollaboratorInviteRequest
from services.permissions import (
    POST_ROLE_CAPABILITIES,
    TOPIC_ROLE_CAPABILITIES,
    can_manage_topic,
)
from services.operators import has_platform_role
from services.notifications import notify
from storage.database.db import get_session
from storage.database.models import (
    AuditLog,
    Post,
    PostCollaborator,
    Topic,
    TopicCollaborator,
    User,
)


router = APIRouter(tags=["permissions"])
VERIFIED_STATUSES = frozenset({"verified", "organization", "campus_verified"})


def _current_user(user_id: str) -> tuple[Any, User]:
    session = get_session()
    try:
        parsed_id = int(user_id)
    except (TypeError, ValueError) as exc:
        session.close()
        raise HTTPException(status_code=401, detail="登录状态已失效") from exc
    user = session.get(User, parsed_id)
    if not user:
        session.close()
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return session, user


def _verified_target(session, value: Any) -> User:
    try:
        user_id = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="目标用户不正确") from exc
    user = session.get(User, user_id)
    if not user or user.auth_status not in VERIFIED_STATUSES:
        raise HTTPException(status_code=404, detail="目标校园认证用户不存在")
    return user


def _parse_expiry(value: Any, default: datetime.datetime) -> datetime.datetime:
    if not value:
        return default
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="权限到期时间格式不正确") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    if parsed <= datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail="权限到期时间必须晚于当前时间")
    return parsed


def _topic_default_expiry(topic: Topic) -> datetime.datetime:
    now = datetime.datetime.now(datetime.timezone.utc)
    if topic.activity_end_at:
        end = topic.activity_end_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)
        if end > now:
            return end + datetime.timedelta(days=30)
    return now + datetime.timedelta(days=180)


def _grant_dict(grant: TopicCollaborator | PostCollaborator) -> dict[str, Any]:
    data = {
        "user_id": str(grant.user_id),
        "role": grant.role,
        "status": grant.status,
        "granted_by": str(grant.granted_by),
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "accepted_at": grant.accepted_at.isoformat() if grant.accepted_at else None,
    }
    if isinstance(grant, TopicCollaborator):
        data["topic_id"] = str(grant.topic_id)
    else:
        data["post_id"] = str(grant.post_id)
    return data


def _audit(session, actor_id: int, action: str, target_type: str, target_id: int, detail: dict) -> None:
    session.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            detail=json.dumps(detail, ensure_ascii=False),
        )
    )


@router.get("/topics/{topic_id}/collaborators")
def list_topic_collaborators(
    topic_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="话题不存在")
        if not can_manage_topic(session, actor, topic, "manage_collaborators"):
            raise HTTPException(status_code=403, detail="你没有管理该话题负责人的权限")
        filters = (TopicCollaborator.topic_id == topic_id,)
        total = int(session.scalar(select(func.count()).select_from(TopicCollaborator).where(*filters)) or 0)
        grants = session.scalars(
            select(TopicCollaborator)
            .where(*filters)
            .order_by(TopicCollaborator.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return api_ok(
            {
                "list": [_grant_dict(grant) for grant in grants],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.post("/topics/{topic_id}/collaborators")
def invite_topic_collaborator(
    topic_id: int,
    body: CollaboratorInviteRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    body = body.model_dump() if isinstance(body, CollaboratorInviteRequest) else body
    session, actor = _current_user(user_id)
    try:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="话题不存在")
        if not can_manage_topic(session, actor, topic, "manage_collaborators"):
            raise HTTPException(status_code=403, detail="你没有管理该话题负责人的权限")
        target = _verified_target(session, body.get("user_id"))
        if target.id == actor.id:
            raise HTTPException(status_code=400, detail="不能邀请自己成为协作者")
        role = str(body.get("role") or "")
        if role not in TOPIC_ROLE_CAPABILITIES:
            raise HTTPException(status_code=400, detail="话题负责人角色不正确")
        expires_at = _parse_expiry(body.get("expires_at"), _topic_default_expiry(topic))
        grant = session.execute(
            select(TopicCollaborator).where(
                TopicCollaborator.topic_id == topic.id,
                TopicCollaborator.user_id == target.id,
            )
        ).scalar_one_or_none()
        if grant:
            grant.role = role
            grant.status = "pending"
            grant.granted_by = actor.id
            grant.accepted_at = None
            grant.revoked_at = None
            grant.expires_at = expires_at
        else:
            grant = TopicCollaborator(
                topic_id=topic.id,
                user_id=target.id,
                role=role,
                status="pending",
                granted_by=actor.id,
                expires_at=expires_at,
            )
            session.add(grant)
        session.flush()
        _audit(session, actor.id, "topic_collaborator.invite", "topic", topic.id, _grant_dict(grant))
        notify(
            session,
            user_id=target.id,
            event_type="topic.collaborator.invited",
            title="收到活动负责人邀请",
            body=f"你被邀请参与管理「{topic.title}」",
            target_type="topic",
            target_id=str(topic.id),
            dedupe_key=f"topic-grant:{grant.id}:invite:{grant.updated_at or grant.created_at}",
        )
        session.commit()
        return api_ok(_grant_dict(grant), "话题负责人邀请已发送")
    finally:
        session.close()


@router.post("/topics/{topic_id}/collaborators/accept")
def accept_topic_collaboration(topic_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        grant = session.execute(
            select(TopicCollaborator).where(
                TopicCollaborator.topic_id == topic_id,
                TopicCollaborator.user_id == actor.id,
            )
        ).scalar_one_or_none()
        if not grant or grant.status != "pending":
            raise HTTPException(status_code=404, detail="没有待接受的话题负责人邀请")
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = grant.expires_at
        if expires and (expires if expires.tzinfo else expires.replace(tzinfo=datetime.timezone.utc)) <= now:
            raise HTTPException(status_code=409, detail="该邀请已经过期")
        grant.status = "active"
        grant.accepted_at = now
        _audit(session, actor.id, "topic_collaborator.accept", "topic", topic_id, _grant_dict(grant))
        session.commit()
        return api_ok(_grant_dict(grant), "已接受话题负责人邀请")
    finally:
        session.close()


@router.delete("/topics/{topic_id}/collaborators/{target_user_id}")
def revoke_topic_collaborator(
    topic_id: int,
    target_user_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="话题不存在")
        if not can_manage_topic(session, actor, topic, "manage_collaborators"):
            raise HTTPException(status_code=403, detail="你没有管理该话题负责人的权限")
        grant = session.execute(
            select(TopicCollaborator).where(
                TopicCollaborator.topic_id == topic_id,
                TopicCollaborator.user_id == target_user_id,
            )
        ).scalar_one_or_none()
        if not grant:
            raise HTTPException(status_code=404, detail="话题负责人授权不存在")
        grant.status = "revoked"
        grant.revoked_at = datetime.datetime.now(datetime.timezone.utc)
        _audit(session, actor.id, "topic_collaborator.revoke", "topic", topic_id, _grant_dict(grant))
        notify(
            session,
            user_id=target_user_id,
            event_type="topic.collaborator.revoked",
            title="活动负责人权限已撤销",
            body=f"你对「{topic.title}」的管理权限已被撤销",
            target_type="topic",
            target_id=str(topic.id),
            dedupe_key=f"topic-grant:{grant.id}:revoked:{grant.revoked_at.isoformat()}",
        )
        session.commit()
        return api_ok(_grant_dict(grant), "话题负责人权限已撤销")
    finally:
        session.close()


def _can_manage_post_collaborators(session, actor: User, post: Post) -> bool:
    return has_platform_role(session, actor) or post.author_id == actor.id


@router.get("/posts/{post_id}/collaborators")
def list_post_collaborators(
    post_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        post = session.get(Post, post_id)
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        if not _can_manage_post_collaborators(session, actor, post):
            raise HTTPException(status_code=403, detail="仅发帖者可以管理帖子协作者")
        filters = (PostCollaborator.post_id == post_id,)
        total = int(session.scalar(select(func.count()).select_from(PostCollaborator).where(*filters)) or 0)
        grants = session.scalars(
            select(PostCollaborator)
            .where(*filters)
            .order_by(PostCollaborator.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return api_ok(
            {
                "list": [_grant_dict(grant) for grant in grants],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.post("/posts/{post_id}/collaborators")
def invite_post_collaborator(
    post_id: int,
    body: CollaboratorInviteRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    body = body.model_dump() if isinstance(body, CollaboratorInviteRequest) else body
    session, actor = _current_user(user_id)
    try:
        post = session.get(Post, post_id)
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        if not _can_manage_post_collaborators(session, actor, post):
            raise HTTPException(status_code=403, detail="仅发帖者可以管理帖子协作者")
        target = _verified_target(session, body.get("user_id"))
        if target.id == actor.id:
            raise HTTPException(status_code=400, detail="不能邀请自己成为协作者")
        role = str(body.get("role") or "")
        if role not in POST_ROLE_CAPABILITIES:
            raise HTTPException(status_code=400, detail="帖子协作者角色不正确")
        expires_at = _parse_expiry(
            body.get("expires_at"),
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=180),
        )
        grant = session.execute(
            select(PostCollaborator).where(
                PostCollaborator.post_id == post.id,
                PostCollaborator.user_id == target.id,
            )
        ).scalar_one_or_none()
        if grant:
            grant.role = role
            grant.status = "pending"
            grant.granted_by = actor.id
            grant.accepted_at = None
            grant.revoked_at = None
            grant.expires_at = expires_at
        else:
            grant = PostCollaborator(
                post_id=post.id,
                user_id=target.id,
                role=role,
                status="pending",
                granted_by=actor.id,
                expires_at=expires_at,
            )
            session.add(grant)
        session.flush()
        _audit(session, actor.id, "post_collaborator.invite", "post", post.id, _grant_dict(grant))
        notify(
            session,
            user_id=target.id,
            event_type="post.collaborator.invited",
            title="收到帖子协作邀请",
            body=f"你被邀请协作管理「{post.title}」",
            target_type="post",
            target_id=str(post.id),
            dedupe_key=f"post-grant:{grant.id}:invite:{grant.updated_at or grant.created_at}",
        )
        session.commit()
        return api_ok(_grant_dict(grant), "帖子协作者邀请已发送")
    finally:
        session.close()


@router.post("/posts/{post_id}/collaborators/accept")
def accept_post_collaboration(post_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        grant = session.execute(
            select(PostCollaborator).where(
                PostCollaborator.post_id == post_id,
                PostCollaborator.user_id == actor.id,
            )
        ).scalar_one_or_none()
        if not grant or grant.status != "pending":
            raise HTTPException(status_code=404, detail="没有待接受的帖子协作者邀请")
        now = datetime.datetime.now(datetime.timezone.utc)
        expires = grant.expires_at
        if expires and (expires if expires.tzinfo else expires.replace(tzinfo=datetime.timezone.utc)) <= now:
            raise HTTPException(status_code=409, detail="该邀请已经过期")
        grant.status = "active"
        grant.accepted_at = now
        _audit(session, actor.id, "post_collaborator.accept", "post", post_id, _grant_dict(grant))
        session.commit()
        return api_ok(_grant_dict(grant), "已接受帖子协作者邀请")
    finally:
        session.close()


@router.delete("/posts/{post_id}/collaborators/{target_user_id}")
def revoke_post_collaborator(
    post_id: int,
    target_user_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        post = session.get(Post, post_id)
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        if not _can_manage_post_collaborators(session, actor, post):
            raise HTTPException(status_code=403, detail="仅发帖者可以管理帖子协作者")
        grant = session.execute(
            select(PostCollaborator).where(
                PostCollaborator.post_id == post_id,
                PostCollaborator.user_id == target_user_id,
            )
        ).scalar_one_or_none()
        if not grant:
            raise HTTPException(status_code=404, detail="帖子协作者授权不存在")
        grant.status = "revoked"
        grant.revoked_at = datetime.datetime.now(datetime.timezone.utc)
        _audit(session, actor.id, "post_collaborator.revoke", "post", post_id, _grant_dict(grant))
        notify(
            session,
            user_id=target_user_id,
            event_type="post.collaborator.revoked",
            title="帖子协作权限已撤销",
            body=f"你对「{post.title}」的协作权限已被撤销",
            target_type="post",
            target_id=str(post.id),
            dedupe_key=f"post-grant:{grant.id}:revoked:{grant.revoked_at.isoformat()}",
        )
        session.commit()
        return api_ok(_grant_dict(grant), "帖子协作者权限已撤销")
    finally:
        session.close()
