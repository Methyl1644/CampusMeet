from __future__ import annotations

import datetime
import json
import os

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from services.participation import deadline_has_passed, set_post_status
from services.notifications import notify
from services.uploads import get_upload_storage
from storage.database.db import get_session
from storage.database.models import (
    Notification,
    Organization,
    OrganizationApplication,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationOwnershipTransfer,
    PlatformRoleGrant,
    Post,
    PostCollaborator,
    TopicCollaborator,
    UploadRecord,
)


def _aware(value: datetime.datetime) -> datetime.datetime:
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


def _expired(value: datetime.datetime | None, now: datetime.datetime) -> bool:
    return value is not None and _aware(value) <= now


def _expire_rows(
    rows: list,
    *,
    now: datetime.datetime,
    current_statuses: set[str],
) -> int:
    changed = 0
    for row in rows:
        if row.status in current_statuses and _expired(row.expires_at, now):
            row.status = "expired"
            changed += 1
    return changed


def _create_expiry_reminders(
    session: Session,
    *,
    now: datetime.datetime,
    reminder_days: int,
) -> int:
    horizon = now + datetime.timedelta(days=max(1, reminder_days))
    reminders: list[tuple[int, str, str, str, str]] = []

    for grant in session.scalars(
        select(PlatformRoleGrant).where(
            PlatformRoleGrant.status == "active",
            PlatformRoleGrant.revoked_at.is_(None),
        )
    ):
        if grant.expires_at and now < _aware(grant.expires_at) <= horizon:
            reminders.append(
                (grant.user_id, "平台运营权限即将到期", "platform_role_grant", str(grant.id), f"platform-role:{grant.id}")
            )

    for model, label, target_type, key_prefix in (
        (TopicCollaborator, "活动负责人权限即将到期", "topic_collaborator", "topic-grant"),
        (PostCollaborator, "帖子协作权限即将到期", "post_collaborator", "post-grant"),
    ):
        for grant in session.scalars(select(model).where(model.status == "active", model.revoked_at.is_(None))):
            if grant.expires_at and now < _aware(grant.expires_at) <= horizon:
                reminders.append(
                    (grant.user_id, label, target_type, str(grant.id), f"{key_prefix}:{grant.id}")
                )

    for membership in session.scalars(
        select(OrganizationMember).where(OrganizationMember.status == "active")
    ):
        if membership.expires_at and now < _aware(membership.expires_at) <= horizon:
            reminders.append(
                (
                    membership.user_id,
                    "组织身份即将到期",
                    "organization",
                    str(membership.organization_id),
                    f"organization-membership:{membership.id}",
                )
            )

    created = 0
    for user_id, title, target_type, target_id, key in reminders:
        dedupe_key = f"expiry-reminder:{key}:{_aware(now).date().isoformat()}"
        if session.scalar(select(Notification.id).where(Notification.dedupe_key == dedupe_key)) is not None:
            continue
        notify(
            session,
            user_id=user_id,
            event_type="permission.expiring",
            title=title,
            body=f"该权限将在 {reminder_days} 天内到期，请及时处理",
            target_type=target_type,
            target_id=target_id,
            dedupe_key=dedupe_key,
        )
        created += 1
    return created


def run_maintenance(
    session: Session,
    *,
    now: datetime.datetime | None = None,
    notification_retention_days: int = 180,
    expiry_reminder_days: int = 7,
    rejected_evidence_retention_days: int = 30,
    storage=None,
) -> dict[str, int]:
    current = _aware(now or datetime.datetime.now(datetime.timezone.utc))
    result = {
        "organizations_expired": 0,
        "memberships_expired": 0,
        "invitations_expired": 0,
        "ownership_transfers_expired": 0,
        "platform_grants_expired": 0,
        "topic_grants_expired": 0,
        "post_grants_expired": 0,
        "posts_closed": 0,
        "uploads_abandoned": 0,
        "rejected_evidence_deleted": 0,
        "notifications_deleted": 0,
        "expiry_reminders_created": 0,
    }

    organizations = list(session.scalars(select(Organization)))
    for organization in organizations:
        if organization.verification_status == "approved" and _expired(organization.expires_at, current):
            organization.verification_status = "expired"
            result["organizations_expired"] += 1

    result["memberships_expired"] = _expire_rows(
        list(session.scalars(select(OrganizationMember))),
        now=current,
        current_statuses={"active"},
    )
    result["invitations_expired"] = _expire_rows(
        list(session.scalars(select(OrganizationInvitation).where(OrganizationInvitation.revoked_at.is_(None)))),
        now=current,
        current_statuses={"pending"},
    )
    result["ownership_transfers_expired"] = _expire_rows(
        list(
            session.scalars(
                select(OrganizationOwnershipTransfer).where(
                    OrganizationOwnershipTransfer.revoked_at.is_(None)
                )
            )
        ),
        now=current,
        current_statuses={"pending"},
    )
    result["platform_grants_expired"] = _expire_rows(
        list(session.scalars(select(PlatformRoleGrant).where(PlatformRoleGrant.revoked_at.is_(None)))),
        now=current,
        current_statuses={"pending", "active"},
    )
    result["topic_grants_expired"] = _expire_rows(
        list(session.scalars(select(TopicCollaborator).where(TopicCollaborator.revoked_at.is_(None)))),
        now=current,
        current_statuses={"pending", "active"},
    )
    result["post_grants_expired"] = _expire_rows(
        list(session.scalars(select(PostCollaborator).where(PostCollaborator.revoked_at.is_(None)))),
        now=current,
        current_statuses={"pending", "active"},
    )

    for post in session.scalars(select(Post).where(Post.status == "recruiting")):
        if deadline_has_passed(post, now=current):
            set_post_status(session, post, "closed")
            post.closed_at = current
            result["posts_closed"] += 1

    for upload in session.scalars(select(UploadRecord).where(UploadRecord.status == "pending")):
        if _expired(upload.expires_at, current):
            upload.status = "abandoned"
            result["uploads_abandoned"] += 1

    if storage is not None:
        evidence_cutoff = current - datetime.timedelta(
            days=max(1, rejected_evidence_retention_days)
        )
        rejected_application_ids = {
            str(application_id)
            for application_id in session.scalars(
                select(OrganizationApplication.id).where(
                    OrganizationApplication.status == "rejected",
                    OrganizationApplication.reviewed_at.is_not(None),
                    OrganizationApplication.reviewed_at < evidence_cutoff,
                )
            )
        }
        if rejected_application_ids:
            evidence_uploads = session.scalars(
                select(UploadRecord).where(
                    UploadRecord.purpose == "organization_evidence",
                    UploadRecord.private.is_(True),
                    UploadRecord.status == "attached",
                    UploadRecord.attached_to_type == "organization_application",
                )
            )
            for upload in evidence_uploads:
                if upload.attached_to_id not in rejected_application_ids:
                    continue
                storage.delete(key=upload.object_key)
                upload.status = "deleted"
                result["rejected_evidence_deleted"] += 1

    result["expiry_reminders_created"] = _create_expiry_reminders(
        session,
        now=current,
        reminder_days=expiry_reminder_days,
    )

    retention_cutoff = current - datetime.timedelta(days=max(1, notification_retention_days))
    deleted = session.execute(
        delete(Notification).where(
            Notification.read_at.is_not(None),
            Notification.created_at < retention_cutoff,
        )
    )
    result["notifications_deleted"] = int(deleted.rowcount or 0)
    return result


def main() -> None:
    retention_days = int(os.getenv("NOTIFICATION_RETENTION_DAYS", "180"))
    reminder_days = int(os.getenv("PERMISSION_EXPIRY_REMINDER_DAYS", "7"))
    evidence_days = int(os.getenv("REJECTED_EVIDENCE_RETENTION_DAYS", "30"))
    try:
        storage = get_upload_storage()
    except RuntimeError:
        storage = None
    session = get_session()
    try:
        result = run_maintenance(
            session,
            notification_retention_days=retention_days,
            expiry_reminder_days=reminder_days,
            rejected_evidence_retention_days=evidence_days,
            storage=storage,
        )
        session.commit()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
