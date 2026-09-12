from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from api.common import api_ok, current_user_id
from api.schemas.operators import (
    PlatformRoleAcceptRequest,
    PlatformRoleActionRequest,
    PlatformRoleInviteRequest,
)
from services import operators as operator_service
from storage.database.db import get_session
from storage.database.models import PlatformRoleGrant, User
from utils.auth import verify_password


router = APIRouter(prefix="/operators", tags=["operators"])


def _current_user(user_id: str) -> tuple[Any, User]:
    session = get_session()
    user = session.get(User, int(user_id))
    if user is None:
        session.close()
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return session, user


def _run_mutation(user_id: str, operation: Callable[[Any, User], PlatformRoleGrant], message: str):
    session, actor = _current_user(user_id)
    try:
        grant = operation(session, actor)
        session.commit()
        return api_ok(operator_service.platform_role_to_dict(grant), message)
    except PermissionError as exc:
        session.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        detail = str(exc)
        status_code = 409 if any(
            marker in detail for marker in ("已有", "已经", "最后一个", "失效", "过期")
        ) else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    finally:
        session.close()


def _role_page(session, filters: tuple[Any, ...], page: int, page_size: int) -> dict[str, Any]:
    total = int(
        session.scalar(select(func.count()).select_from(PlatformRoleGrant).where(*filters)) or 0
    )
    rows = session.scalars(
        select(PlatformRoleGrant)
        .where(*filters)
        .order_by(PlatformRoleGrant.created_at.desc(), PlatformRoleGrant.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "list": [operator_service.platform_role_to_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/roles/my")
def my_platform_roles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        return api_ok(
            _role_page(session, (PlatformRoleGrant.user_id == actor.id,), page, page_size)
        )
    finally:
        session.close()


@router.get("/roles")
def list_platform_roles(
    status: str = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    if status not in {"pending", "active", "suspended", "revoked", "expired", "all"}:
        raise HTTPException(status_code=400, detail="平台角色状态不正确")
    session, actor = _current_user(user_id)
    try:
        if not operator_service.has_platform_role(session, actor):
            raise HTTPException(status_code=403, detail="仅平台运营可以查看角色清单")
        filters = () if status == "all" else (PlatformRoleGrant.status == status,)
        return api_ok(_role_page(session, filters, page, page_size))
    finally:
        session.close()


@router.post("/roles/invitations")
def invite_platform_role(
    body: PlatformRoleInviteRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    if isinstance(body, PlatformRoleInviteRequest):
        body = body.model_dump()
    def operation(session, actor):
        try:
            target_user_id = int(body.get("user_id") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("目标用户编号不正确") from exc
        target = session.get(User, target_user_id)
        if target is None:
            raise ValueError("目标用户不存在")
        return operator_service.invite_platform_role(
            session,
            actor,
            target,
            role=str(body.get("role") or ""),
        )

    return _run_mutation(user_id, operation, "平台角色邀请已发送")


@router.post("/roles/{grant_id}/accept")
def accept_platform_role(
    grant_id: int,
    body: PlatformRoleAcceptRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    def operation(session, actor):
        grant = session.get(PlatformRoleGrant, grant_id)
        if grant is None:
            raise ValueError("平台角色邀请不存在")
        password = body.password if isinstance(body, PlatformRoleAcceptRequest) else str(body.get("password") or "")
        return operator_service.accept_platform_role(
            session,
            actor,
            grant,
            recent_reauthenticated=verify_password(password, actor.password_hash),
        )

    return _run_mutation(user_id, operation, "平台角色已生效")


@router.post("/roles/{grant_id}/suspend")
def suspend_platform_role(
    grant_id: int,
    body: PlatformRoleActionRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    if isinstance(body, PlatformRoleActionRequest):
        body = body.model_dump()
    def operation(session, actor):
        grant = session.get(PlatformRoleGrant, grant_id)
        if grant is None:
            raise ValueError("平台角色不存在")
        return operator_service.suspend_platform_role(
            session,
            actor,
            grant,
            reason=str(body.get("reason") or "")[:500],
        )

    return _run_mutation(user_id, operation, "平台角色已暂停")


@router.post("/roles/{grant_id}/revoke")
def revoke_platform_role(
    grant_id: int,
    body: PlatformRoleActionRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    if isinstance(body, PlatformRoleActionRequest):
        body = body.model_dump()
    def operation(session, actor):
        grant = session.get(PlatformRoleGrant, grant_id)
        if grant is None:
            raise ValueError("平台角色不存在")
        return operator_service.revoke_platform_role(
            session,
            actor,
            grant,
            reason=str(body.get("reason") or "")[:500],
        )

    return _run_mutation(user_id, operation, "平台角色已撤销")
