from __future__ import annotations

import datetime
import json

from sqlalchemy.orm import Session

from services.permissions import can_manage_post
from storage.database.models import Application, AuditLog, Post, User


PUBLIC_POST_STATUSES = ("recruiting", "full", "closed")


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
        parsed = datetime.datetime.combine(parsed_date, datetime.time.max, tzinfo=datetime.timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed <= (now or utcnow())


def application_availability_error(post: Post, *, now: datetime.datetime | None = None) -> str | None:
    if post.status != "recruiting":
        return "该帖子已停止招募"
    if post.current_members >= post.target_members:
        return "队伍已满员"
    if deadline_has_passed(post, now=now):
        return "招募已过截止时间"
    return None


def _audit(session: Session, actor_id: int, action: str, post: Post) -> None:
    session.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            target_type="post",
            target_id=str(post.id),
            detail=json.dumps({"status": post.status}, ensure_ascii=False),
        )
    )


def transition_post(session: Session, actor: User, post: Post, action: str) -> Post:
    if not can_manage_post(session, actor, post, "update_status"):
        raise PermissionError("你没有更新该帖子状态的权限")
    now = utcnow()
    if action == "close":
        if post.status in {"archived", "deleted"}:
            raise ValueError("当前帖子不能关闭")
        post.status = "closed"
        post.closed_at = now
    elif action == "reopen":
        if post.status in {"archived", "deleted"}:
            raise ValueError("归档或删除的帖子不能重新招募")
        if deadline_has_passed(post, now=now):
            raise ValueError("招募已过截止时间")
        post.status = "full" if post.current_members >= post.target_members else "recruiting"
    elif action == "archive":
        if post.status == "deleted":
            raise ValueError("已删除的帖子不能归档")
        post.status = "archived"
        post.archived_at = now
    elif action == "delete":
        post.status = "deleted"
        post.deleted_at = now
    else:
        raise ValueError("帖子状态操作不受支持")
    _audit(session, actor.id, f"post.{action}", post)
    return post


def withdraw_application(session: Session, actor: User, application: Application) -> Application:
    if application.applicant_id != actor.id:
        raise PermissionError("只能撤回自己的申请")
    if application.status == "withdrawn":
        return application
    if application.status != "pending":
        raise ValueError("只有待处理的申请可以撤回")
    application.status = "withdrawn"
    application.withdrawn_at = utcnow()
    session.add(
        AuditLog(
            user_id=actor.id,
            action="application.withdraw",
            target_type="application",
            target_id=str(application.id),
            detail=json.dumps({"post_id": application.post_id}, ensure_ascii=False),
        )
    )
    return application
