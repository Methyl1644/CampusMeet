from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from api.common import api_ok, current_user_id
from api.schemas.identity import (
    OrganizationApplicationRequest,
    OrganizationInvitationRequest,
    OrganizationRenewalRequest,
    OrganizationReviewRequest,
    OwnershipTransferRequest,
)
from services.identity import (
    accept_invitation,
    active_organization_owner,
    application_to_dict,
    complete_ownership_transfer,
    create_invitation,
    create_ownership_transfer,
    invitation_to_dict,
    is_operator,
    list_applications,
    ownership_transfer_to_dict,
    review_application,
    submit_application,
    utcnow,
)
from storage.database.db import get_session
from storage.database.models import (
    AuditLog,
    Organization,
    OrganizationApplication,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationOwnershipTransfer,
    User,
)


router = APIRouter(tags=["identity"])


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


def _body(value: Any) -> dict[str, Any]:
    return value.model_dump() if hasattr(value, "model_dump") else dict(value)


def _domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    status = 409 if any(word in str(exc) for word in ("已有", "已经", "过期", "不可用")) else 400
    return HTTPException(status_code=status, detail=str(exc))


@router.post("/organizations/applications")
def submit_organization_application(
    body: OrganizationApplicationRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        try:
            application = submit_application(session, user, _body(body))
            session.commit()
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise _domain_error(exc) from exc
        return api_ok(application_to_dict(application), "申请已提交")
    finally:
        session.close()


@router.get("/organizations/applications/my")
def my_organization_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        rows, total = list_applications(
            session,
            applicant_id=user.id,
            page=page,
            page_size=page_size,
        )
        return api_ok(
            {
                "list": [application_to_dict(row) for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.get("/operators/organization-applications")
def organization_application_queue(
    status: str = Query(default="pending"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        if not is_operator(session, user):
            raise HTTPException(status_code=403, detail="仅平台运营可以查看审核队列")
        if status not in {"pending", "approved", "rejected", "expired", "all"}:
            raise HTTPException(status_code=400, detail="申请状态不正确")
        rows, total = list_applications(session, status=status, page=page, page_size=page_size)
        return api_ok(
            {
                "list": [application_to_dict(row) for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.get("/operators/organization-applications/{application_id}")
def organization_application_detail(
    application_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        if not is_operator(session, user):
            raise HTTPException(status_code=403, detail="仅平台运营可以查看证明材料")
        application = session.get(OrganizationApplication, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="组织申请不存在")
        return api_ok(application_to_dict(application, include_private=True))
    finally:
        session.close()


@router.post("/operators/organization-applications/{application_id}/review")
def review_organization_application(
    application_id: int,
    body: OrganizationReviewRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, reviewer = _current_user(user_id)
    try:
        application = session.get(OrganizationApplication, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="组织申请不存在")
        payload = _body(body)
        try:
            organization = review_application(
                session,
                reviewer,
                application,
                decision=payload["decision"],
                reason=payload.get("reason") or "",
                validity_days=int(payload.get("validity_days") or 365),
            )
            session.commit()
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise _domain_error(exc) from exc
        return api_ok(
            {
                "application_id": str(application.id),
                "status": application.status,
                "organization_id": str(organization.id) if organization else None,
            },
            "审核已完成",
        )
    finally:
        session.close()


@router.post("/organizations/applications/{application_id}/renew")
def renew_organization_application(
    application_id: int,
    body: OrganizationRenewalRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        previous = session.get(OrganizationApplication, application_id)
        if not previous or previous.applicant_id != user.id:
            raise HTTPException(status_code=404, detail="组织申请不存在")
        payload = _body(body)
        payload.update(
            {
                "organization_name": previous.organization_name,
                "org_type": previous.org_type,
                "official_email": previous.official_email,
            }
        )
        try:
            renewal = submit_application(session, user, payload)
            session.commit()
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise _domain_error(exc) from exc
        return api_ok(application_to_dict(renewal), "续期申请已提交")
    finally:
        session.close()


@router.post("/organizations/{organization_id}/invitations")
def invite_organization_member(
    organization_id: int,
    body: OrganizationInvitationRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        organization = session.get(Organization, organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="组织不存在")
        payload = _body(body)
        invitee = session.get(User, int(payload["user_id"]))
        if not invitee:
            raise HTTPException(status_code=404, detail="目标用户不存在")
        try:
            invitation = create_invitation(
                session,
                actor,
                organization,
                invitee,
                role=str(payload["role"]),
                expires_at=payload.get("expires_at"),
            )
            session.commit()
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise _domain_error(exc) from exc
        return api_ok(invitation_to_dict(invitation), "成员邀请已发送")
    finally:
        session.close()


@router.get("/organizations/invitations/my")
def my_organization_invitations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        filters = (OrganizationInvitation.invitee_id == actor.id,)
        total = int(session.scalar(select(func.count()).select_from(OrganizationInvitation).where(*filters)) or 0)
        invitations = session.scalars(
            select(OrganizationInvitation)
            .where(*filters)
            .order_by(OrganizationInvitation.created_at.desc(), OrganizationInvitation.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return api_ok(
            {
                "list": [invitation_to_dict(invitation) for invitation in invitations],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


def _pending_invitation(session, invitation_id: int) -> OrganizationInvitation:
    invitation = session.get(OrganizationInvitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="组织邀请不存在")
    return invitation


@router.post("/organizations/invitations/{invitation_id}/accept")
def accept_organization_invitation(
    invitation_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        invitation = _pending_invitation(session, invitation_id)
        try:
            accept_invitation(session, actor, invitation)
            session.commit()
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise _domain_error(exc) from exc
        return api_ok(invitation_to_dict(invitation), "已加入组织")
    finally:
        session.close()


@router.post("/organizations/invitations/{invitation_id}/decline")
def decline_organization_invitation(
    invitation_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        invitation = _pending_invitation(session, invitation_id)
        if invitation.invitee_id != actor.id:
            raise HTTPException(status_code=403, detail="只有受邀用户可以拒绝邀请")
        if invitation.status != "pending" or invitation.revoked_at is not None:
            raise HTTPException(status_code=409, detail="邀请已经处理")
        invitation.status = "declined"
        session.add(
            AuditLog(
                user_id=actor.id,
                action="organization.invitation.decline",
                target_type="organization_invitation",
                target_id=str(invitation.id),
                detail='{"status":"declined"}',
            )
        )
        session.commit()
        return api_ok(invitation_to_dict(invitation), "已拒绝邀请")
    finally:
        session.close()


@router.get("/organizations/{organization_id}/members")
def organization_members(
    organization_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        organization = session.get(Organization, organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="组织不存在")
        if not active_organization_owner(session, organization, actor.id) and not is_operator(session, actor):
            raise HTTPException(status_code=403, detail="无权查看组织成员")
        filters = (OrganizationMember.organization_id == organization_id,)
        total = int(session.scalar(select(func.count()).select_from(OrganizationMember).where(*filters)) or 0)
        members = session.scalars(
            select(OrganizationMember)
            .where(*filters)
            .order_by(OrganizationMember.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return api_ok(
            {
                "list": [
                    {
                        "user_id": str(member.user_id),
                        "role": member.role,
                        "status": member.status,
                        "effective_at": member.effective_at.isoformat() if member.effective_at else None,
                        "expires_at": member.expires_at.isoformat() if member.expires_at else None,
                    }
                    for member in members
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.delete("/organizations/{organization_id}/members/{target_user_id}")
def revoke_organization_member(
    organization_id: int,
    target_user_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        organization = session.get(Organization, organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="组织不存在")
        if not active_organization_owner(session, organization, actor.id) and not is_operator(session, actor):
            raise HTTPException(status_code=403, detail="仅组织负责人可以撤销成员")
        membership = session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == target_user_id,
                OrganizationMember.status == "active",
            )
        ).scalar_one_or_none()
        if not membership:
            raise HTTPException(status_code=404, detail="有效成员不存在")
        if membership.role == "owner":
            owners = session.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role == "owner",
                    OrganizationMember.status == "active",
                )
            ).scalars().all()
            if len(owners) <= 1:
                raise HTTPException(status_code=409, detail="最后一位负责人必须先完成负责人转移")
        membership.status = "revoked"
        session.add(
            AuditLog(
                user_id=actor.id,
                action="organization.member.revoke",
                target_type="organization_member",
                target_id=str(membership.id),
                detail=f'{{"organization_id":{organization_id},"user_id":{target_user_id}}}',
            )
        )
        session.commit()
        return api_ok({"user_id": str(target_user_id), "status": membership.status}, "成员权限已撤销")
    finally:
        session.close()


@router.post("/organizations/{organization_id}/ownership-transfers")
def create_organization_ownership_transfer(
    organization_id: int,
    body: OwnershipTransferRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        organization = session.get(Organization, organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="组织不存在")
        payload = _body(body)
        successor = session.get(User, int(payload["target_user_id"]))
        if not successor:
            raise HTTPException(status_code=404, detail="接任用户不存在")
        try:
            transfer = create_ownership_transfer(
                session,
                actor,
                organization,
                successor,
                expires_at=payload.get("expires_at"),
            )
            session.commit()
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise _domain_error(exc) from exc
        return api_ok(ownership_transfer_to_dict(transfer), "负责人转移邀请已发送")
    finally:
        session.close()


@router.get("/organizations/ownership-transfers/my")
def my_organization_ownership_transfers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        filters = (OrganizationOwnershipTransfer.to_owner_id == actor.id,)
        total = int(
            session.scalar(
                select(func.count()).select_from(OrganizationOwnershipTransfer).where(*filters)
            )
            or 0
        )
        transfers = session.scalars(
            select(OrganizationOwnershipTransfer).where(
                *filters
            )
            .order_by(OrganizationOwnershipTransfer.created_at.desc(), OrganizationOwnershipTransfer.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return api_ok(
            {
                "list": [ownership_transfer_to_dict(transfer) for transfer in transfers],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.post("/organizations/ownership-transfers/{transfer_id}/accept")
def accept_organization_ownership_transfer(
    transfer_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        transfer = session.get(OrganizationOwnershipTransfer, transfer_id)
        if not transfer:
            raise HTTPException(status_code=404, detail="负责人转移不存在")
        try:
            complete_ownership_transfer(session, actor, transfer)
            session.commit()
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise _domain_error(exc) from exc
        return api_ok(ownership_transfer_to_dict(transfer), "负责人转移已完成")
    finally:
        session.close()
