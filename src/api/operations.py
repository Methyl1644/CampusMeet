from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from api.common import api_ok, current_user_id
from services.observability import metrics_snapshot, redact_sensitive
from services.operators import has_platform_role
from storage.database.db import get_session
from storage.database.models import (
    Appeal,
    AuditLog,
    ModerationCase,
    OrganizationApplication,
    User,
)


router = APIRouter(prefix="/operators", tags=["operations"])


def _operator_session(user_id: str):
    session = get_session()
    actor = session.get(User, int(user_id))
    if actor is None or not has_platform_role(session, actor):
        session.close()
        raise HTTPException(status_code=403, detail="仅平台运营可以查看运营数据")
    return session


def _audit_to_dict(item: AuditLog) -> dict[str, Any]:
    try:
        detail = json.loads(item.detail) if item.detail else {}
    except (json.JSONDecodeError, TypeError):
        detail = {}
    return {
        "id": str(item.id),
        "actor_id": str(item.user_id) if item.user_id is not None else None,
        "action": item.action,
        "target_type": item.target_type,
        "target_id": item.target_id,
        "detail": redact_sensitive(detail),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.get("/audit-logs")
def search_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str = Query(default="", max_length=100),
    target_type: str = Query(default="", max_length=80),
    actor_id: int | None = Query(default=None, ge=1),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = _operator_session(user_id)
    try:
        filters = []
        if action:
            filters.append(AuditLog.action.contains(action))
        if target_type:
            filters.append(AuditLog.target_type == target_type)
        if actor_id is not None:
            filters.append(AuditLog.user_id == actor_id)
        total = int(session.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0)
        rows = session.scalars(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return api_ok(
            {
                "list": [_audit_to_dict(item) for item in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.get("/metrics")
def operational_metrics(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = _operator_session(user_id)
    try:
        queues = {
            "moderation_cases_open": int(
                session.scalar(
                    select(func.count()).select_from(ModerationCase).where(ModerationCase.status == "open")
                )
                or 0
            ),
            "appeals_pending": int(
                session.scalar(select(func.count()).select_from(Appeal).where(Appeal.status == "pending"))
                or 0
            ),
            "organization_applications_pending": int(
                session.scalar(
                    select(func.count())
                    .select_from(OrganizationApplication)
                    .where(OrganizationApplication.status == "pending")
                )
                or 0
            ),
        }
        return api_ok({"process": metrics_snapshot(), "queues": queues})
    finally:
        session.close()
