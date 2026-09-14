from __future__ import annotations

import datetime
import json
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from services.operators import active_platform_grants, has_platform_role, is_configured_staff
from services.notifications import notify
from storage.database.models import (
    AuditLog,
    Organization,
    OrganizationApplication,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationOwnershipTransfer,
    Post,
    PostCollaborator,
    Topic,
    TopicCollaborator,
    User,
)


CAMPUS_VERIFIED_STATUSES = frozenset({"verified", "organization", "campus_verified"})


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def aware(value: datetime.datetime) -> datetime.datetime:
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


def is_operator(session: Session, user: User) -> bool:
    return has_platform_role(session, user)


def organization_is_active(organization: Organization, *, now: datetime.datetime | None = None) -> bool:
    current = now or utcnow()
    return bool(
        organization.verification_status == "approved"
        and (organization.expires_at is None or aware(organization.expires_at) > current)
    )


def active_organization_owner(
    session: Session,
    organization: Organization,
    user_id: int,
) -> OrganizationMember | None:
    if not organization_is_active(organization):
        return None
    membership = session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.role == "owner",
            OrganizationMember.status == "active",
        )
    ).scalar_one_or_none()
    if not membership:
        return None
    if membership.expires_at and aware(membership.expires_at) <= utcnow():
        return None
    return membership


def _audit(
    session: Session,
    actor_id: int,
    action: str,
    target_type: str,
    target_id: int | None,
    detail: dict[str, Any],
) -> None:
    session.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            detail=json.dumps(detail, ensure_ascii=False),
        )
    )


def application_status(application: OrganizationApplication) -> str:
    if (
        application.status == "approved"
        and application.expires_at
        and aware(application.expires_at) <= utcnow()
    ):
        return "expired"
    return application.status


def application_to_dict(
    application: OrganizationApplication,
    *,
    include_private: bool = False,
) -> dict[str, Any]:
    data = {
        "application_id": str(application.id),
        "organization_name": application.organization_name,
        "org_type": application.org_type,
        "school_scope": application.school_scope,
        "official_email": application.official_email,
        "official_page": application.official_page,
        "status": application_status(application),
        "review_reason": application.review_reason,
        "reviewed_at": application.reviewed_at.isoformat() if application.reviewed_at else None,
        "expires_at": application.expires_at.isoformat() if application.expires_at else None,
        "created_at": application.created_at.isoformat() if application.created_at else None,
    }
    if include_private:
        data.update(
            {
                "applicant_id": str(application.applicant_id),
                "responsible_person_statement": application.responsible_person_statement,
                "evidence_reference": application.evidence_reference or application.evidence,
            }
        )
    return data


def submit_application(
    session: Session,
    user: User,
    payload: dict[str, Any],
) -> OrganizationApplication:
    if user.auth_status not in CAMPUS_VERIFIED_STATUSES:
        raise PermissionError("请先完成校园认证")
    name = str(payload["organization_name"]).strip()
    existing = session.execute(
        select(OrganizationApplication).where(
            OrganizationApplication.applicant_id == user.id,
            OrganizationApplication.organization_name == name,
            OrganizationApplication.status == "pending",
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("该组织已有待审核申请")
    evidence_reference = str(payload.get("evidence_reference") or payload.get("evidence") or "").strip()
    upload = None
    if evidence_reference.startswith("upload:"):
        from storage.database.models import UploadRecord

        upload = session.get(UploadRecord, evidence_reference.removeprefix("upload:"))
        if upload is None:
            raise ValueError("认证材料上传记录不存在")
        if upload.owner_id != user.id:
            raise PermissionError("无权使用该认证材料")
        if (
            upload.purpose != "organization_evidence"
            or not upload.private
            or upload.status != "completed"
        ):
            raise ValueError("认证材料未完成校验或用途不正确")
        evidence_reference = upload.object_key
    application = OrganizationApplication(
        applicant_id=user.id,
        organization_name=name,
        org_type=str(payload["org_type"]),
        school_scope=str(payload["school_scope"]),
        official_email=str(payload.get("official_email") or "").strip() or None,
        official_page=str(payload.get("official_page") or "").strip() or None,
        responsible_person_statement=str(payload["responsible_person_statement"]),
        evidence_reference=evidence_reference,
        evidence=str(payload.get("evidence") or evidence_reference),
        status="pending",
    )
    session.add(application)
    session.flush()
    if upload is not None:
        upload.status = "attached"
        upload.attached_to_type = "organization_application"
        upload.attached_to_id = str(application.id)
    _audit(
        session,
        user.id,
        "organization.application.submit",
        "organization_application",
        application.id,
        {"organization_name": name},
    )
    return application


def review_application(
    session: Session,
    reviewer: User,
    application: OrganizationApplication,
    *,
    decision: str,
    reason: str,
    validity_days: int,
) -> Organization | None:
    if not is_operator(session, reviewer):
        raise PermissionError("仅平台运营可以审核组织")
    if application.applicant_id == reviewer.id:
        raise PermissionError("不能审核自己的组织申请")
    if application.status != "pending":
        raise ValueError("该申请已经处理")

    now = utcnow()
    application.status = "approved" if decision == "approve" else "rejected"
    application.reviewed_by = reviewer.id
    application.reviewed_at = now
    application.review_reason = reason or None
    organization = None

    if decision == "approve":
        expires_at = now + datetime.timedelta(days=validity_days)
        application.expires_at = expires_at
        organization = session.execute(
            select(Organization).where(Organization.name == application.organization_name)
        ).scalar_one_or_none()
        if organization is None:
            organization = Organization(
                name=application.organization_name,
                org_type=application.org_type,
                school_scope=application.school_scope,
            )
            session.add(organization)
            session.flush()
        current_owner = session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.role == "owner",
                OrganizationMember.status == "active",
            )
        ).scalar_one_or_none()
        if current_owner and current_owner.user_id != application.applicant_id:
            raise ValueError("该组织已有有效负责人，请使用成员邀请或负责人转移流程")
        organization.org_type = application.org_type
        organization.school_scope = application.school_scope
        organization.verification_status = "approved"
        organization.verified_at = now
        organization.expires_at = expires_at
        membership = session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.user_id == application.applicant_id,
            )
        ).scalar_one_or_none()
        if membership is None:
            membership = OrganizationMember(
                organization_id=organization.id,
                user_id=application.applicant_id,
            )
            session.add(membership)
        membership.role = "owner"
        membership.status = "active"
        membership.invited_by = reviewer.id
        membership.effective_at = now
        membership.expires_at = expires_at

    _audit(
        session,
        reviewer.id,
        f"organization.application.{decision}",
        "organization_application",
        application.id,
        {"reason": reason, "validity_days": validity_days if decision == "approve" else None},
    )
    notify(
        session,
        user_id=application.applicant_id,
        event_type=f"organization.application.{application.status}",
        title="组织认证审核已完成",
        body=(
            f"「{application.organization_name}」已通过认证"
            if application.status == "approved"
            else f"「{application.organization_name}」认证申请未通过"
        ),
        target_type="organization_application",
        target_id=str(application.id),
        dedupe_key=f"organization-application:{application.id}:{application.status}",
    )
    return organization


def invitation_to_dict(invitation: OrganizationInvitation) -> dict[str, Any]:
    return {
        "invitation_id": str(invitation.id),
        "organization_id": str(invitation.organization_id),
        "inviter_id": str(invitation.inviter_id),
        "invitee_id": str(invitation.invitee_id),
        "role": invitation.requested_role,
        "status": invitation.status,
        "expires_at": invitation.expires_at.isoformat(),
        "accepted_at": invitation.accepted_at.isoformat() if invitation.accepted_at else None,
        "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
    }


def ownership_transfer_to_dict(transfer: OrganizationOwnershipTransfer) -> dict[str, Any]:
    return {
        "transfer_id": str(transfer.id),
        "organization_id": str(transfer.organization_id),
        "from_owner_id": str(transfer.from_owner_id),
        "to_owner_id": str(transfer.to_owner_id),
        "status": transfer.status,
        "expires_at": transfer.expires_at.isoformat(),
        "accepted_at": transfer.accepted_at.isoformat() if transfer.accepted_at else None,
        "completed_at": transfer.completed_at.isoformat() if transfer.completed_at else None,
    }


def create_ownership_transfer(
    session: Session,
    actor: User,
    organization: Organization,
    successor: User,
    *,
    expires_at: datetime.datetime | None,
) -> OrganizationOwnershipTransfer:
    owner = active_organization_owner(session, organization, actor.id)
    if not owner:
        raise PermissionError("仅当前组织负责人可以发起负责人转移")
    if successor.id == actor.id:
        raise ValueError("不能向自己转移负责人身份")
    successor_membership = session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == successor.id,
            OrganizationMember.status == "active",
        )
    ).scalar_one_or_none()
    if not successor_membership:
        raise ValueError("新负责人必须先接受组织成员邀请")
    duplicate = session.execute(
        select(OrganizationOwnershipTransfer).where(
            OrganizationOwnershipTransfer.organization_id == organization.id,
            OrganizationOwnershipTransfer.status == "pending",
            OrganizationOwnershipTransfer.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if duplicate:
        raise ValueError("该组织已有待处理的负责人转移")
    now = utcnow()
    default_expiry = now + datetime.timedelta(days=7)
    if organization.expires_at and aware(organization.expires_at) < default_expiry:
        default_expiry = aware(organization.expires_at)
    transfer = OrganizationOwnershipTransfer(
        organization_id=organization.id,
        from_owner_id=actor.id,
        to_owner_id=successor.id,
        initiated_by=actor.id,
        status="pending",
        expires_at=expires_at or default_expiry,
    )
    session.add(transfer)
    session.flush()
    _audit(
        session,
        actor.id,
        "organization.ownership_transfer.create",
        "organization_ownership_transfer",
        transfer.id,
        {"organization_id": organization.id, "to_owner_id": successor.id},
    )
    notify(
        session,
        user_id=successor.id,
        event_type="organization.ownership_transfer.created",
        title="收到负责人转移邀请",
        body=f"你被邀请接任「{organization.name}」负责人",
        target_type="organization_ownership_transfer",
        target_id=str(transfer.id),
        dedupe_key=f"organization-transfer:{transfer.id}:created",
    )
    return transfer


def complete_ownership_transfer(
    session: Session,
    actor: User,
    transfer: OrganizationOwnershipTransfer,
) -> None:
    if transfer.to_owner_id != actor.id:
        raise PermissionError("只有指定的新负责人可以接受转移")
    if transfer.status != "pending" or transfer.revoked_at is not None:
        raise ValueError("负责人转移已经处理")
    now = utcnow()
    if aware(transfer.expires_at) <= now:
        transfer.status = "expired"
        raise ValueError("负责人转移已经过期")
    organization = session.get(Organization, transfer.organization_id)
    if not organization or not organization_is_active(organization, now=now):
        raise ValueError("组织认证已过期或不可用")
    current_owner = session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == transfer.from_owner_id,
            OrganizationMember.role == "owner",
            OrganizationMember.status == "active",
        )
    ).scalar_one_or_none()
    successor = session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == actor.id,
            OrganizationMember.status == "active",
        )
    ).scalar_one_or_none()
    if not current_owner or not successor:
        raise ValueError("负责人或接任人的组织成员状态已经变化")
    current_owner.role = "member"
    session.flush()
    successor.role = "owner"
    successor.effective_at = now
    transfer.status = "completed"
    transfer.accepted_at = now
    transfer.completed_at = now
    _audit(
        session,
        actor.id,
        "organization.ownership_transfer.complete",
        "organization_ownership_transfer",
        transfer.id,
        {"organization_id": organization.id, "from_owner_id": transfer.from_owner_id},
    )
    notify(
        session,
        user_id=transfer.from_owner_id,
        event_type="organization.ownership_transfer.completed",
        title="负责人转移已完成",
        body=f"「{organization.name}」负责人已成功转移",
        target_type="organization",
        target_id=str(organization.id),
        dedupe_key=f"organization-transfer:{transfer.id}:completed",
    )


def create_invitation(
    session: Session,
    actor: User,
    organization: Organization,
    invitee: User,
    *,
    role: str,
    expires_at: datetime.datetime | None,
) -> OrganizationInvitation:
    if not organization_is_active(organization):
        raise ValueError("组织认证已过期或不可用")
    if not active_organization_owner(session, organization, actor.id):
        raise PermissionError("仅组织负责人可以邀请成员")
    if invitee.auth_status not in CAMPUS_VERIFIED_STATUSES:
        raise ValueError("只能邀请已完成校园认证的用户")
    if invitee.id == actor.id:
        raise ValueError("不能邀请自己")
    duplicate = session.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == organization.id,
            OrganizationInvitation.invitee_id == invitee.id,
            OrganizationInvitation.status == "pending",
            OrganizationInvitation.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if duplicate:
        raise ValueError("该用户已有待处理邀请")
    now = utcnow()
    default_expiry = now + datetime.timedelta(days=14)
    if organization.expires_at and aware(organization.expires_at) < default_expiry:
        default_expiry = aware(organization.expires_at)
    invitation = OrganizationInvitation(
        organization_id=organization.id,
        inviter_id=actor.id,
        invitee_id=invitee.id,
        requested_role=role,
        status="pending",
        expires_at=expires_at or default_expiry,
    )
    session.add(invitation)
    session.flush()
    _audit(
        session,
        actor.id,
        "organization.invitation.create",
        "organization_invitation",
        invitation.id,
        {"organization_id": organization.id, "invitee_id": invitee.id, "role": role},
    )
    notify(
        session,
        user_id=invitee.id,
        event_type="organization.invitation.created",
        title="收到组织邀请",
        body=f"你被邀请加入「{organization.name}」",
        target_type="organization_invitation",
        target_id=str(invitation.id),
        dedupe_key=f"organization-invitation:{invitation.id}:created",
    )
    return invitation


def accept_invitation(
    session: Session,
    actor: User,
    invitation: OrganizationInvitation,
) -> OrganizationMember:
    if invitation.invitee_id != actor.id:
        raise PermissionError("只有受邀用户可以接受邀请")
    if invitation.status != "pending" or invitation.revoked_at is not None:
        raise ValueError("邀请已经处理")
    now = utcnow()
    if aware(invitation.expires_at) <= now:
        invitation.status = "expired"
        raise ValueError("邀请已经过期")
    organization = session.get(Organization, invitation.organization_id)
    if not organization or not organization_is_active(organization, now=now):
        raise ValueError("组织认证已过期或不可用")
    membership = session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == actor.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        membership = OrganizationMember(organization_id=organization.id, user_id=actor.id)
        session.add(membership)
    membership.role = invitation.requested_role
    membership.status = "active"
    membership.invited_by = invitation.inviter_id
    membership.effective_at = now
    membership.expires_at = organization.expires_at
    invitation.status = "accepted"
    invitation.accepted_at = now
    _audit(
        session,
        actor.id,
        "organization.invitation.accept",
        "organization_invitation",
        invitation.id,
        {"organization_id": organization.id, "role": invitation.requested_role},
    )
    notify(
        session,
        user_id=invitation.inviter_id,
        event_type="organization.invitation.accepted",
        title="组织邀请已接受",
        body=f"{actor.nickname} 已加入「{organization.name}」",
        target_type="organization",
        target_id=str(organization.id),
        dedupe_key=f"organization-invitation:{invitation.id}:accepted",
    )
    return membership


def list_applications(
    session: Session,
    *,
    applicant_id: int | None = None,
    status: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[OrganizationApplication], int]:
    query = select(OrganizationApplication)
    if applicant_id is not None:
        query = query.where(OrganizationApplication.applicant_id == applicant_id)
    if status not in {"all", "expired"}:
        query = query.where(OrganizationApplication.status == status)
    rows = session.execute(query.order_by(desc(OrganizationApplication.created_at))).scalars().all()
    if status == "expired":
        rows = [row for row in rows if application_status(row) == "expired"]
    total = len(rows)
    start = (page - 1) * page_size
    return rows[start : start + page_size], total


def _grant_is_active(status: str, expires_at: datetime.datetime | None) -> bool:
    return status == "active" and (expires_at is None or aware(expires_at) > utcnow())


def identity_summary(session: Session, user: User) -> dict[str, Any]:
    platform_grants = active_platform_grants(session, user.id)
    platform_role = None
    if platform_grants:
        role_priority = {"operator": 1, "senior_operator": 2}
        platform_role = max(
            (grant.role for grant in platform_grants),
            key=role_priority.__getitem__,
        )
    elif user.site_role in {"operator", "senior_operator"}:
        platform_role = user.site_role
    if is_configured_staff(user):
        platform_role = "senior_operator"

    organization_roles: list[dict[str, Any]] = []
    memberships = session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    ).scalars().all()
    for membership in memberships:
        organization = session.get(Organization, membership.organization_id)
        if (
            not organization
            or not organization_is_active(organization)
            or not _grant_is_active(membership.status, membership.expires_at)
        ):
            continue
        organization_roles.append(
            {
                "organization_id": str(organization.id),
                "organization_name": organization.name,
                "role": membership.role,
                "expires_at": membership.expires_at.isoformat() if membership.expires_at else None,
            }
        )

    topic_roles: list[dict[str, Any]] = []
    for grant in session.execute(
        select(TopicCollaborator).where(TopicCollaborator.user_id == user.id)
    ).scalars().all():
        topic = session.get(Topic, grant.topic_id)
        if not topic or topic.status != "active" or not _grant_is_active(grant.status, grant.expires_at):
            continue
        topic_roles.append(
            {
                "topic_id": str(topic.id),
                "topic_title": topic.title,
                "role": grant.role,
                "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            }
        )

    post_roles: list[dict[str, Any]] = []
    for grant in session.execute(
        select(PostCollaborator).where(PostCollaborator.user_id == user.id)
    ).scalars().all():
        post = session.get(Post, grant.post_id)
        if not post or not _grant_is_active(grant.status, grant.expires_at):
            continue
        post_roles.append(
            {
                "post_id": str(post.id),
                "post_title": post.title,
                "role": grant.role,
                "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            }
        )

    return {
        "campus_verified": user.auth_status in CAMPUS_VERIFIED_STATUSES,
        "is_staff": is_configured_staff(user),
        "platform_role": platform_role,
        "organization_roles": organization_roles,
        "topic_roles": topic_roles,
        "post_roles": post_roles,
    }


def managed_organizations(session: Session, user: User) -> list[dict[str, Any]]:
    memberships = session.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.role == "owner",
            OrganizationMember.status == "active",
        )
    ).scalars().all()
    result: list[dict[str, Any]] = []
    for membership in memberships:
        organization = session.get(Organization, membership.organization_id)
        if (
            not organization
            or not organization_is_active(organization)
            or not _grant_is_active(membership.status, membership.expires_at)
        ):
            continue
        result.append(
            {
                "organization_id": str(organization.id),
                "organization_name": organization.name,
                "role": membership.role,
                "expires_at": membership.expires_at.isoformat()
                if membership.expires_at
                else None,
            }
        )
    return sorted(result, key=lambda item: item["organization_name"].casefold())


def topic_trust_projection(session: Session, topic: Topic) -> dict[str, Any]:
    if topic.status != "active":
        return {"trust_badges": [], "responsible_people": []}
    badges: list[dict[str, str]] = []
    if topic.channel == "official":
        badges.append({"kind": "platform_official", "label": "平台官方收录"})
    elif topic.channel == "organization" and topic.organization_id:
        organization = session.get(Organization, topic.organization_id)
        if organization and organization_is_active(organization):
            badges.append(
                {
                    "kind": "verified_organization",
                    "label": "认证组织发布",
                    "organization_name": organization.name,
                }
            )

    responsible_people: list[dict[str, str]] = []
    role_badges = {
        "manager": "活动负责人",
        "editor": "活动组织者",
        "coordinator": "活动协作成员",
    }
    grants = session.execute(
        select(TopicCollaborator).where(TopicCollaborator.topic_id == topic.id)
    ).scalars().all()
    for grant in grants:
        if not _grant_is_active(grant.status, grant.expires_at):
            continue
        user = session.get(User, grant.user_id)
        if not user:
            continue
        responsible_people.append(
            {
                "user_id": str(user.id),
                "nickname": user.nickname,
                "role": grant.role,
                "badge": role_badges.get(grant.role, "活动协作者"),
            }
        )
    return {"trust_badges": badges, "responsible_people": responsible_people}


def post_trust_projection(session: Session, post: Post) -> dict[str, Any]:
    collaborators: list[dict[str, str]] = []
    grants = session.execute(
        select(PostCollaborator).where(PostCollaborator.post_id == post.id)
    ).scalars().all()
    for grant in grants:
        if not _grant_is_active(grant.status, grant.expires_at):
            continue
        user = session.get(User, grant.user_id)
        if not user:
            continue
        collaborators.append(
            {
                "user_id": str(user.id),
                "nickname": user.nickname,
                "role": grant.role,
                "badge": "帖子协作者",
            }
        )
    return {"collaborators": collaborators}
