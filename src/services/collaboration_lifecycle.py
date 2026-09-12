from __future__ import annotations

import json

from sqlalchemy.orm import Session

from services.participation import deadline_has_passed, transition_post_status, utcnow
from storage.database.models import Application, AuditLog, Post, User


PUBLIC_POST_STATUSES = ("recruiting", "full", "closed")


def application_availability_error(post: Post, *, now=None) -> str | None:
    if post.status != "recruiting":
        return "该帖子已停止招募"
    if post.current_members >= post.target_members:
        return "队伍已满员"
    if deadline_has_passed(post, now=now):
        return "招募已过截止时间"
    return None


def transition_post(session: Session, actor: User, post: Post, action: str) -> Post:
    return transition_post_status(session, actor, post, action)


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
