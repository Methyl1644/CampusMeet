from __future__ import annotations

import datetime
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from api.common import api_ok, current_user_id
from api.schemas.moderation import (
    AppealCreateRequest,
    AppealReviewRequest,
    CaseResolutionRequest,
    ReportCreateRequest,
    RestrictionCreateRequest,
)
from services import moderation_cases
from storage.database.db import get_session
from storage.database.models import Appeal, ModerationCase, ModerationEvent, Report, User, UserBlock


router = APIRouter(prefix="/moderation", tags=["moderation"])


def _current_user(user_id: str) -> tuple[Any, User]:
    session = get_session()
    try:
        parsed_id = int(user_id)
    except (TypeError, ValueError) as exc:
        session.close()
        raise HTTPException(status_code=401, detail="登录状态已失效") from exc
    user = session.get(User, parsed_id)
    if user is None:
        session.close()
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return session, user


def _domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    status = 409 if any(word in str(exc) for word in ("已经", "已处理", "未屏蔽")) else 400
    return HTTPException(status_code=status, detail=str(exc))


def _mutation(user_id: str, operation: Callable[[Any, User], Any]) -> Any:
    session, actor = _current_user(user_id)
    try:
        try:
            result = operation(session, actor)
            session.commit()
            return result
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise _domain_error(exc) from exc
    finally:
        session.close()


def _positive_page(page: int, page_size: int) -> None:
    if page < 1 or not 1 <= page_size <= 50:
        raise HTTPException(status_code=422, detail="分页参数不正确")


def _parse_datetime(value: Any) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        parsed = value
    else:
        try:
            parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("限制结束时间格式不正确") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


@router.post("/reports")
def create_report(body: ReportCreateRequest, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    body = body.model_dump() if isinstance(body, ReportCreateRequest) else body
    def operation(session, actor):
        report, case, merged = moderation_cases.create_report(
            session,
            actor,
            target_type=str(body.get("target_type") or ""),
            target_id=str(body.get("target_id") or ""),
            reason_code=str(body.get("reason_code") or ""),
            description=body.get("description"),
        )
        return api_ok(
            {
                "report": moderation_cases.report_to_dict(report),
                "case": moderation_cases.case_to_dict(case),
                "merged": merged,
            },
            "举报信息已补充" if merged else "举报已提交",
        )

    return _mutation(user_id, operation)


@router.get("/reports/my")
def my_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    _positive_page(page, page_size)
    session, actor = _current_user(user_id)
    try:
        rows, total = moderation_cases.list_user_reports(
            session, actor, page=page, page_size=page_size
        )
        return api_ok(
            {
                "list": [moderation_cases.report_to_dict(row) for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.post("/blocks/{target_user_id}")
def block_user(target_user_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    def operation(session, actor):
        target = session.get(User, target_user_id)
        if target is None:
            raise ValueError("目标用户不存在")
        moderation_cases.block_user(session, actor, target)
        return api_ok({"blocked_user_id": str(target.id), "blocked": True}, "已屏蔽该用户")

    return _mutation(user_id, operation)


@router.delete("/blocks/{target_user_id}")
def unblock_user(target_user_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    def operation(session, actor):
        target = session.get(User, target_user_id)
        if target is None:
            raise ValueError("目标用户不存在")
        moderation_cases.unblock_user(session, actor, target)
        return api_ok({"blocked_user_id": str(target.id), "blocked": False}, "已取消屏蔽")

    return _mutation(user_id, operation)


@router.get("/blocks/my")
def my_blocks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        filters = (UserBlock.blocker_id == actor.id, UserBlock.revoked_at.is_(None))
        total = int(session.scalar(select(func.count()).select_from(UserBlock).where(*filters)) or 0)
        rows = session.scalars(
            select(UserBlock).where(
                *filters
            )
            .order_by(UserBlock.created_at.desc(), UserBlock.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return api_ok(
            {
                "list": [
                    {
                        "id": str(row.id),
                        "blocked_user_id": str(row.blocked_id),
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
                    for row in rows
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.get("/operator/cases")
def operator_case_queue(
    status: str = Query(default="open"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    _positive_page(page, page_size)
    if status not in {"open", "resolved", "dismissed", "all"}:
        raise HTTPException(status_code=400, detail="案件状态不正确")
    session, actor = _current_user(user_id)
    try:
        try:
            rows, total = moderation_cases.list_cases(
                session, actor, status=status, page=page, page_size=page_size
            )
        except PermissionError as exc:
            raise _domain_error(exc) from exc
        return api_ok(
            {
                "list": [moderation_cases.case_to_dict(row) for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.get("/operator/cases/{case_id}")
def operator_case_detail(
    case_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        try:
            case = moderation_cases.get_case(session, actor, case_id)
        except (PermissionError, ValueError) as exc:
            raise _domain_error(exc) from exc
        payload = moderation_cases.case_to_dict(case)
        report = session.get(Report, case.report_id) if case.report_id is not None else None
        event = session.get(ModerationEvent, case.event_id) if case.event_id is not None else None
        payload["report"] = moderation_cases.report_to_dict(report) if report is not None else None
        payload["event"] = moderation_cases.event_to_dict(event) if event is not None else None
        return api_ok(payload)
    finally:
        session.close()


def _close_case_api(
    case_id: int,
    body: dict[str, Any],
    user_id: str,
    *,
    dismiss: bool,
) -> dict[str, Any]:
    def operation(session, actor):
        case = session.get(ModerationCase, case_id)
        if case is None:
            raise ValueError("审核案件不存在")
        service = moderation_cases.dismiss_case if dismiss else moderation_cases.resolve_case
        service(session, actor, case, resolution=str(body.get("resolution") or ""))
        return api_ok(
            moderation_cases.case_to_dict(case),
            "案件已驳回" if dismiss else "案件已处理",
        )

    return _mutation(user_id, operation)


@router.post("/operator/cases/{case_id}/resolve")
def resolve_case(
    case_id: int,
    body: CaseResolutionRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    payload = body.model_dump() if isinstance(body, CaseResolutionRequest) else body
    return _close_case_api(case_id, payload, user_id, dismiss=False)


@router.post("/operator/cases/{case_id}/dismiss")
def dismiss_case(
    case_id: int,
    body: CaseResolutionRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    payload = body.model_dump() if isinstance(body, CaseResolutionRequest) else body
    return _close_case_api(case_id, payload, user_id, dismiss=True)


@router.post("/operator/cases/{case_id}/restrictions")
def create_account_restriction(
    case_id: int,
    body: RestrictionCreateRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    body = body.model_dump() if isinstance(body, RestrictionCreateRequest) else body
    def operation(session, actor):
        case = session.get(ModerationCase, case_id)
        if case is None:
            raise ValueError("审核案件不存在")
        try:
            target_user_id = int(body.get("user_id") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("目标用户编号不正确") from exc
        target = session.get(User, target_user_id)
        if target is None:
            raise ValueError("目标用户不存在")
        restriction = moderation_cases.create_restriction(
            session,
            actor,
            case,
            target,
            restriction_type=str(body.get("restriction_type") or ""),
            reason_code=str(body.get("reason_code") or ""),
            expires_at=_parse_datetime(body.get("expires_at")),
        )
        return api_ok(moderation_cases.restriction_to_dict(restriction), "临时限制已生效")

    return _mutation(user_id, operation)


@router.post("/appeals")
def submit_appeal(body: AppealCreateRequest, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    body = body.model_dump() if isinstance(body, AppealCreateRequest) else body
    def operation(session, actor):
        try:
            case_id = int(body.get("case_id") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("案件编号不正确") from exc
        case = session.get(ModerationCase, case_id)
        if case is None:
            raise ValueError("审核案件不存在")
        appeal = moderation_cases.submit_appeal(
            session, actor, case, statement=str(body.get("statement") or "")
        )
        return api_ok(moderation_cases.appeal_to_dict(appeal), "申诉已提交")

    return _mutation(user_id, operation)


@router.get("/appeals/my")
def my_appeals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    _positive_page(page, page_size)
    session, actor = _current_user(user_id)
    try:
        rows, total = moderation_cases.list_appeals(
            session, actor, page=page, page_size=page_size
        )
        return api_ok(
            {
                "list": [moderation_cases.appeal_to_dict(row) for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.get("/operator/appeals")
def operator_appeal_queue(
    status: str = Query(default="pending"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    _positive_page(page, page_size)
    if status not in {"pending", "approved", "rejected", "all"}:
        raise HTTPException(status_code=400, detail="申诉状态不正确")
    session, actor = _current_user(user_id)
    try:
        try:
            rows, total = moderation_cases.list_appeals(
                session,
                actor,
                page=page,
                page_size=page_size,
                operator_queue=True,
                status=status,
            )
        except PermissionError as exc:
            raise _domain_error(exc) from exc
        return api_ok(
            {
                "list": [moderation_cases.appeal_to_dict(row) for row in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()


@router.post("/operator/appeals/{appeal_id}/resolve")
def review_appeal(
    appeal_id: int,
    body: AppealReviewRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    body = body.model_dump() if isinstance(body, AppealReviewRequest) else body
    def operation(session, actor):
        appeal = session.get(Appeal, appeal_id)
        if appeal is None:
            raise ValueError("申诉不存在")
        moderation_cases.review_appeal(
            session,
            actor,
            appeal,
            outcome=str(body.get("outcome") or ""),
            resolution=str(body.get("resolution") or ""),
        )
        return api_ok(moderation_cases.appeal_to_dict(appeal), "申诉已处理")

    return _mutation(user_id, operation)
