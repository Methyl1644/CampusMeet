from __future__ import annotations

import datetime
import json
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.database.models import AuditLog, PlatformRoleGrant, User
from services.notifications import notify


PLATFORM_ROLES = frozenset({"operator", "senior_operator"})
_ROLE_PRIORITY = {"operator": 1, "senior_operator": 2}


def configured_staff_emails() -> frozenset[str]:
    return frozenset(
        item.strip().casefold()
        for item in os.getenv("STAFF_EMAILS", "").split(",")
        if item.strip()
    )


def is_configured_staff(user: User) -> bool:
    return (user.email or "").strip().casefold() in configured_staff_emails()


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _aware(value: datetime.datetime) -> datetime.datetime:
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


def _is_active(grant: PlatformRoleGrant, *, now: datetime.datetime | None = None) -> bool:
    current = now or utcnow()
    return bool(
        grant.status == "active"
        and grant.revoked_at is None
        and (grant.expires_at is None or _aware(grant.expires_at) > current)
    )


def _audit(
    session: Session,
    actor_id: int,
    action: str,
    grant: PlatformRoleGrant,
    detail: dict[str, Any],
) -> None:
    session.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            target_type="platform_role_grant",
            target_id=str(grant.id),
            detail=json.dumps(detail, ensure_ascii=False),
        )
    )


def platform_role_to_dict(grant: PlatformRoleGrant) -> dict[str, Any]:
    return {
        "grant_id": str(grant.id),
        "user_id": str(grant.user_id),
        "role": grant.role,
        "status": grant.status,
        "granted_by": str(grant.granted_by),
        "accepted_at": grant.accepted_at.isoformat() if grant.accepted_at else None,
        "effective_at": grant.effective_at.isoformat() if grant.effective_at else None,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None,
    }


def active_platform_grants(session: Session, user_id: int) -> list[PlatformRoleGrant]:
    grants = session.execute(
        select(PlatformRoleGrant).where(
            PlatformRoleGrant.user_id == user_id,
            PlatformRoleGrant.status == "active",
            PlatformRoleGrant.revoked_at.is_(None),
        )
    ).scalars().all()
    return [grant for grant in grants if _is_active(grant)]


def has_platform_role(
    session: Session,
    user: User,
    roles: frozenset[str] = PLATFORM_ROLES,
) -> bool:
    if is_configured_staff(user) and roles.intersection(PLATFORM_ROLES):
        return True
    grants = active_platform_grants(session, user.id)
    if grants:
        return any(grant.role in roles for grant in grants)
    has_governed_roles = session.execute(select(PlatformRoleGrant.id).limit(1)).first() is not None
    return not has_governed_roles and user.site_role in roles


def _materialize_configured_staff(session: Session, user: User) -> PlatformRoleGrant | None:
    if not is_configured_staff(user):
        return None
    existing = next(
        (grant for grant in active_platform_grants(session, user.id) if grant.role == "senior_operator"),
        None,
    )
    if existing:
        return existing
    now = utcnow()
    grant = PlatformRoleGrant(
        user_id=user.id,
        role="senior_operator",
        status="active",
        granted_by=user.id,
        accepted_at=now,
        effective_at=now,
    )
    session.add(grant)
    session.flush()
    user.site_role = "senior_operator"
    _audit(session, user.id, "platform_role.staff_bootstrap", grant, {"source": "STAFF_EMAILS"})
    return grant


def bootstrap_configured_staff(session: Session) -> int:
    created = 0
    if not configured_staff_emails():
        return created
    users = session.execute(select(User).where(User.email.in_(configured_staff_emails()))).scalars().all()
    for user in users:
        before = len(active_platform_grants(session, user.id))
        _materialize_configured_staff(session, user)
        created += int(before == 0)
    return created


def bootstrap_platform_operator(session: Session, email: str) -> bool:
    normalized = email.strip().casefold()
    if not normalized or session.execute(select(PlatformRoleGrant.id).limit(1)).first() is not None:
        return False
    user = session.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if not user or user.auth_status not in {"verified", "organization", "campus_verified"}:
        return False
    now = utcnow()
    grant = PlatformRoleGrant(
        user_id=user.id,
        role="senior_operator",
        status="active",
        granted_by=user.id,
        accepted_at=now,
        effective_at=now,
    )
    session.add(grant)
    session.flush()
    user.site_role = "senior_operator"
    _audit(session, user.id, "platform_role.bootstrap", grant, {"role": grant.role, "source": "configured_email"})
    return True


def _bootstrap_legacy_operator(
    session: Session,
    user: User,
) -> PlatformRoleGrant | None:
    if session.execute(select(PlatformRoleGrant.id).limit(1)).first() is not None:
        return None

    configured_email = os.getenv("BOOTSTRAP_OPERATOR_EMAIL", "").strip().casefold()
    user_email = (user.email or "").strip().casefold()
    is_configured_legacy_operator = bool(
        configured_email
        and user_email == configured_email
        and user.site_role in PLATFORM_ROLES
    )
    is_explicit_legacy_senior = user.site_role == "senior_operator"
    if not (is_configured_legacy_operator or is_explicit_legacy_senior):
        return None

    now = utcnow()
    grant = PlatformRoleGrant(
        user_id=user.id,
        role="senior_operator",
        status="active",
        granted_by=user.id,
        accepted_at=now,
        effective_at=now,
    )
    session.add(grant)
    session.flush()
    user.site_role = "senior_operator"
    _audit(
        session,
        user.id,
        "platform_role.bootstrap",
        grant,
        {"role": grant.role, "source": "legacy_site_role"},
    )
    return grant


def require_senior_operator(session: Session, user: User) -> PlatformRoleGrant:
    grants = active_platform_grants(session, user.id)
    senior = next((grant for grant in grants if grant.role == "senior_operator"), None)
    if senior is None:
        senior = _materialize_configured_staff(session, user)
    if senior is None:
        senior = _bootstrap_legacy_operator(session, user)
    if senior is None:
        raise PermissionError("仅高级平台运营可以管理平台角色")
    return senior


def invite_platform_role(
    session: Session,
    actor: User,
    target: User,
    *,
    role: str,
) -> PlatformRoleGrant:
    require_senior_operator(session, actor)
    if role not in PLATFORM_ROLES:
        raise ValueError("平台角色只能是 operator 或 senior_operator")
    if actor.id == target.id:
        raise PermissionError("不能为自己授予或提升平台角色")
    if target.auth_status not in {"verified", "organization", "campus_verified"}:
        raise ValueError("目标账号必须先完成校园认证")

    current = session.execute(
        select(PlatformRoleGrant).where(
            PlatformRoleGrant.user_id == target.id,
            PlatformRoleGrant.role == role,
            PlatformRoleGrant.status.in_(("pending", "active")),
            PlatformRoleGrant.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if current is not None:
        raise ValueError("该用户已有待接受或生效中的同类平台角色")

    grant = PlatformRoleGrant(
        user_id=target.id,
        role=role,
        status="pending",
        granted_by=actor.id,
    )
    session.add(grant)
    session.flush()
    _audit(
        session,
        actor.id,
        "platform_role.invite",
        grant,
        {"target_user_id": target.id, "role": role},
    )
    notify(
        session,
        user_id=target.id,
        event_type="platform_role.invited",
        title="收到平台角色邀请",
        body=f"你被邀请担任 {role}",
        target_type="platform_role_grant",
        target_id=str(grant.id),
        dedupe_key=f"platform-role:{grant.id}:invited",
    )
    return grant


def accept_platform_role(
    session: Session,
    user: User,
    grant: PlatformRoleGrant,
    *,
    recent_reauthenticated: bool,
) -> PlatformRoleGrant:
    if not recent_reauthenticated:
        raise PermissionError("接受平台角色前需要重新验证身份")
    if grant.user_id != user.id:
        raise PermissionError("只能接受发给自己的平台角色邀请")
    if grant.granted_by == user.id:
        raise PermissionError("不能审核或接受自己发起的平台角色授权")
    if grant.status != "pending" or grant.revoked_at is not None:
        raise ValueError("该平台角色邀请已失效或已经处理")
    if grant.expires_at is not None and _aware(grant.expires_at) <= utcnow():
        raise ValueError("该平台角色邀请已过期")

    now = utcnow()
    grant.status = "active"
    grant.accepted_at = now
    grant.effective_at = now
    user.site_role = grant.role
    _audit(
        session,
        user.id,
        "platform_role.accept",
        grant,
        {"role": grant.role, "granted_by": grant.granted_by},
    )
    return grant


def decline_platform_role(
    session: Session,
    user: User,
    grant: PlatformRoleGrant,
) -> PlatformRoleGrant:
    if grant.user_id != user.id:
        raise PermissionError("只能拒绝发给自己的平台角色邀请")
    if grant.status != "pending" or grant.revoked_at is not None:
        raise ValueError("该平台角色邀请已失效或已经处理")
    grant.status = "revoked"
    grant.revoked_at = utcnow()
    _audit(
        session,
        user.id,
        "platform_role.decline",
        grant,
        {"role": grant.role, "granted_by": grant.granted_by},
    )
    notify(
        session,
        user_id=grant.granted_by,
        event_type="platform_role.declined",
        title="平台角色邀请已被拒绝",
        body=f"{user.nickname} 拒绝了 {grant.role} 邀请",
        target_type="platform_role_grant",
        target_id=str(grant.id),
        dedupe_key=f"platform-role:{grant.id}:declined",
    )
    return grant


def _active_senior_count(session: Session) -> int:
    grants = session.execute(
        select(PlatformRoleGrant).where(
            PlatformRoleGrant.role == "senior_operator",
            PlatformRoleGrant.status == "active",
            PlatformRoleGrant.revoked_at.is_(None),
        )
    ).scalars().all()
    return sum(1 for grant in grants if _is_active(grant))


def _protect_last_senior(session: Session, grant: PlatformRoleGrant) -> None:
    if grant.role == "senior_operator" and _is_active(grant) and _active_senior_count(session) <= 1:
        raise ValueError("不能停用或撤销最后一个有效的高级平台运营")


def _sync_legacy_site_role(session: Session, user_id: int) -> None:
    user = session.get(User, user_id)
    if user is None:
        return
    roles = [grant.role for grant in active_platform_grants(session, user_id)]
    user.site_role = max(roles, key=_ROLE_PRIORITY.__getitem__) if roles else "student"


def suspend_platform_role(
    session: Session,
    actor: User,
    grant: PlatformRoleGrant,
    *,
    reason: str,
) -> PlatformRoleGrant:
    require_senior_operator(session, actor)
    if grant.status != "active" or not _is_active(grant):
        raise ValueError("只能暂停当前有效的平台角色")
    _protect_last_senior(session, grant)
    grant.status = "suspended"
    _sync_legacy_site_role(session, grant.user_id)
    _audit(
        session,
        actor.id,
        "platform_role.suspend",
        grant,
        {"target_user_id": grant.user_id, "role": grant.role, "reason": reason},
    )
    notify(
        session,
        user_id=grant.user_id,
        event_type="platform_role.suspended",
        title="平台角色已暂停",
        body="你的平台运营权限已暂停，请联系高级运营了解详情",
        target_type="platform_role_grant",
        target_id=str(grant.id),
        dedupe_key=f"platform-role:{grant.id}:suspended:{utcnow().isoformat()}",
    )
    return grant


def revoke_platform_role(
    session: Session,
    actor: User,
    grant: PlatformRoleGrant,
    *,
    reason: str,
) -> PlatformRoleGrant:
    require_senior_operator(session, actor)
    if grant.status not in {"pending", "active", "suspended"} or grant.revoked_at is not None:
        raise ValueError("该平台角色已经撤销")
    _protect_last_senior(session, grant)
    grant.status = "revoked"
    grant.revoked_at = utcnow()
    _sync_legacy_site_role(session, grant.user_id)
    _audit(
        session,
        actor.id,
        "platform_role.revoke",
        grant,
        {"target_user_id": grant.user_id, "role": grant.role, "reason": reason},
    )
    notify(
        session,
        user_id=grant.user_id,
        event_type="platform_role.revoked",
        title="平台角色已撤销",
        body="你的平台运营权限已撤销",
        target_type="platform_role_grant",
        target_id=str(grant.id),
        dedupe_key=f"platform-role:{grant.id}:revoked",
    )
    return grant
