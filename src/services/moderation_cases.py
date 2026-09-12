from __future__ import annotations

import datetime
import json
import re
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from services.operators import has_platform_role
from services.notifications import notify
from storage.database.models import (
    AccountRestriction,
    Appeal,
    AuditLog,
    Message,
    ModerationCase,
    ModerationEvent,
    Post,
    Report,
    Topic,
    User,
    UserBlock,
)


TARGET_MODELS = {
    "post": Post,
    "topic": Topic,
    "message": Message,
    "user": User,
}
OPERATOR_ROLES = frozenset({"operator", "senior_operator"})
RESTRICTION_TYPES = frozenset({"posting", "messaging", "applications", "all_interactions"})
CASE_FINAL_STATUSES = frozenset({"resolved", "dismissed"})
_PHONE_RE = re.compile(r"(?<!\d)(1\d{2})\d{4}(\d{4})(?!\d)")
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
_CONTACT_ID_RE = re.compile(r"(?i)((?:微信|微.?信|vx|v信|qq)\s*[:：号]?\s*)[A-Z0-9_-]{4,}")


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _aware(value: datetime.datetime) -> datetime.datetime:
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


def _audit(
    session: Session,
    actor_id: int | None,
    action: str,
    target_type: str,
    target_id: int | str,
    detail: dict[str, Any],
) -> None:
    session.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            detail=json.dumps(detail, ensure_ascii=False, separators=(",", ":")),
        )
    )


def mask_excerpt(raw_text: str, *, max_length: int = 160) -> str:
    text = " ".join(str(raw_text or "").split())
    text = _URL_RE.sub("[链接已隐藏]", text)
    text = _EMAIL_RE.sub("[邮箱已隐藏]", text)
    text = _PHONE_RE.sub(r"\1****\2", text)
    text = _CONTACT_ID_RE.sub(r"\1[账号已隐藏]", text)
    return text[:max_length]


def record_moderation_event(
    session: Session,
    *,
    actor_id: int | None,
    surface: str,
    target_type: str | None,
    target_id: str | None,
    action: str,
    risk_level: str,
    rule_ids: list[str],
    raw_excerpt: str,
    source: str,
) -> ModerationEvent:
    stable_rules = list(dict.fromkeys(str(item)[:100] for item in rule_ids if str(item).strip()))[:20]
    event = ModerationEvent(
        actor_id=actor_id,
        surface=surface,
        target_type=target_type,
        target_id=target_id,
        action=action,
        risk_level=risk_level,
        rule_ids=stable_rules,
        excerpt=mask_excerpt(raw_excerpt),
        source=source,
    )
    session.add(event)
    session.flush()
    _audit(
        session,
        actor_id,
        "moderation_event.record",
        "moderation_event",
        event.id,
        {
            "surface": surface,
            "action": action,
            "risk_level": risk_level,
            "rule_ids": stable_rules,
        },
    )
    return event


def _target_and_subject(session: Session, target_type: str, target_id: str) -> tuple[Any, int | None]:
    model = TARGET_MODELS.get(target_type)
    if model is None:
        raise ValueError("举报目标类型不受支持")
    try:
        parsed_id = int(target_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("举报目标编号不正确") from exc
    target = session.get(model, parsed_id)
    if target is None:
        raise ValueError("举报目标不存在")
    if target_type == "user":
        subject_user_id = target.id
    elif target_type == "post":
        subject_user_id = target.author_id
    elif target_type == "topic":
        subject_user_id = target.created_by
    else:
        subject_user_id = target.sender_id
    return target, subject_user_id


def create_case_from_event(
    session: Session,
    event: ModerationEvent,
    *,
    subject_user_id: int | None,
    reason_code: str,
    priority: str = "normal",
) -> ModerationCase:
    if event.id is None:
        session.flush()
    if not event.target_type or not event.target_id:
        raise ValueError("只有关联具体目标的审核事件可以创建案件")
    if priority not in {"low", "normal", "high", "urgent"}:
        raise ValueError("案件优先级不正确")
    if not reason_code.strip():
        raise ValueError("案件原因不能为空")
    existing = session.execute(
        select(ModerationCase).where(ModerationCase.event_id == event.id)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("该审核事件已经创建案件")
    case = ModerationCase(
        event_id=event.id,
        target_type=event.target_type,
        target_id=event.target_id,
        subject_user_id=subject_user_id,
        reason_code=reason_code.strip()[:100],
        priority=priority,
    )
    session.add(case)
    session.flush()
    _audit(
        session,
        event.actor_id,
        "moderation_case.create",
        "moderation_case",
        case.id,
        {
            "event_id": event.id,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "reason_code": case.reason_code,
            "priority": priority,
        },
    )
    return case


def create_report(
    session: Session,
    reporter: User,
    *,
    target_type: str,
    target_id: str,
    reason_code: str,
    description: str | None = None,
) -> tuple[Report, ModerationCase, bool]:
    if not reason_code.strip():
        raise ValueError("请选择举报原因")
    _, subject_user_id = _target_and_subject(session, target_type, target_id)
    if target_type == "user" and subject_user_id == reporter.id:
        raise ValueError("不能举报自己")

    report = session.execute(
        select(Report).where(
            Report.reporter_id == reporter.id,
            Report.target_type == target_type,
            Report.target_id == str(target_id),
            Report.status == "open",
        )
    ).scalar_one_or_none()
    if report is not None:
        report.report_count += 1
        report.reason_code = reason_code.strip()[:100]
        if description is not None:
            report.description = description.strip()[:2000] or None
        case = session.execute(
            select(ModerationCase).where(
                ModerationCase.report_id == report.id,
                ModerationCase.status.not_in(CASE_FINAL_STATUSES),
            )
        ).scalar_one()
        _audit(
            session,
            reporter.id,
            "report.merge",
            "report",
            report.id,
            {"target_type": target_type, "target_id": str(target_id), "report_count": report.report_count},
        )
        return report, case, True

    report = Report(
        reporter_id=reporter.id,
        target_type=target_type,
        target_id=str(target_id),
        reason_code=reason_code.strip()[:100],
        description=(description or "").strip()[:2000] or None,
    )
    session.add(report)
    session.flush()
    case = ModerationCase(
        report_id=report.id,
        target_type=target_type,
        target_id=str(target_id),
        subject_user_id=subject_user_id,
        reason_code=report.reason_code,
    )
    session.add(case)
    session.flush()
    safe_target = {"target_type": target_type, "target_id": str(target_id), "reason_code": report.reason_code}
    _audit(session, reporter.id, "report.create", "report", report.id, safe_target)
    _audit(session, reporter.id, "moderation_case.create", "moderation_case", case.id, safe_target)
    return report, case, False


def list_user_reports(
    session: Session,
    user: User,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Report], int]:
    filters = (Report.reporter_id == user.id,)
    total = session.scalar(select(func.count()).select_from(Report).where(*filters)) or 0
    rows = session.execute(
        select(Report)
        .where(*filters)
        .order_by(Report.created_at.desc(), Report.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), int(total)


def block_user(session: Session, blocker: User, blocked: User) -> UserBlock:
    if blocker.id == blocked.id:
        raise ValueError("不能屏蔽自己")
    current = session.execute(
        select(UserBlock).where(
            UserBlock.blocker_id == blocker.id,
            UserBlock.blocked_id == blocked.id,
            UserBlock.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if current is not None:
        return current
    block = UserBlock(blocker_id=blocker.id, blocked_id=blocked.id)
    session.add(block)
    session.flush()
    _audit(
        session,
        blocker.id,
        "user_block.create",
        "user_block",
        block.id,
        {"blocked_id": blocked.id},
    )
    return block


def unblock_user(session: Session, blocker: User, blocked: User) -> UserBlock:
    block = session.execute(
        select(UserBlock).where(
            UserBlock.blocker_id == blocker.id,
            UserBlock.blocked_id == blocked.id,
            UserBlock.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if block is None:
        raise ValueError("当前未屏蔽该用户")
    block.revoked_at = utcnow()
    _audit(
        session,
        blocker.id,
        "user_block.revoke",
        "user_block",
        block.id,
        {"blocked_id": blocked.id},
    )
    return block


def users_are_blocked(session: Session, first_user_id: int, second_user_id: int) -> bool:
    if first_user_id == second_user_id:
        return False
    return session.execute(
        select(UserBlock.id).where(
            UserBlock.revoked_at.is_(None),
            or_(
                and_(UserBlock.blocker_id == first_user_id, UserBlock.blocked_id == second_user_id),
                and_(UserBlock.blocker_id == second_user_id, UserBlock.blocked_id == first_user_id),
            ),
        ).limit(1)
    ).first() is not None


def require_operator(session: Session, actor: User) -> None:
    if not has_platform_role(session, actor, OPERATOR_ROLES):
        raise PermissionError("仅平台运营可以执行该操作")


def list_cases(
    session: Session,
    actor: User,
    *,
    page: int,
    page_size: int,
    status: str = "open",
) -> tuple[list[ModerationCase], int]:
    require_operator(session, actor)
    filters = () if status == "all" else (ModerationCase.status == status,)
    total = session.scalar(select(func.count()).select_from(ModerationCase).where(*filters)) or 0
    rows = session.execute(
        select(ModerationCase)
        .where(*filters)
        .order_by(ModerationCase.created_at.asc(), ModerationCase.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), int(total)


def get_case(session: Session, actor: User, case_id: int) -> ModerationCase:
    require_operator(session, actor)
    case = session.get(ModerationCase, case_id)
    if case is None:
        raise ValueError("审核案件不存在")
    return case


def _close_case(
    session: Session,
    actor: User,
    case: ModerationCase,
    *,
    status: str,
    resolution: str,
) -> ModerationCase:
    require_operator(session, actor)
    if case.status in CASE_FINAL_STATUSES:
        raise ValueError("审核案件已经处理")
    if not resolution.strip():
        raise ValueError("请填写处理结论")
    now = utcnow()
    case.status = status
    case.assigned_operator_id = actor.id
    case.resolution = resolution.strip()[:500]
    case.resolved_at = now
    action_verb = {"resolved": "resolve", "dismissed": "dismiss"}[status]
    if case.report_id is not None:
        report = session.get(Report, case.report_id)
        if report is not None:
            report.status = status
            report.assigned_operator_id = actor.id
            report.resolution = case.resolution
            report.resolved_at = now
            _audit(
                session,
                actor.id,
                f"report.{action_verb}",
                "report",
                report.id,
                {"status": status, "case_id": case.id},
            )
            notify(
                session,
                user_id=report.reporter_id,
                event_type=f"moderation.report.{status}",
                title="举报处理已完成",
                body="你提交的举报已有处理结果",
                target_type="report",
                target_id=str(report.id),
                dedupe_key=f"report:{report.id}:{status}",
            )
    _audit(
        session,
        actor.id,
        f"moderation_case.{action_verb}",
        "moderation_case",
        case.id,
        {"status": status, "reason_code": case.reason_code},
    )
    return case


def resolve_case(session: Session, actor: User, case: ModerationCase, *, resolution: str) -> ModerationCase:
    return _close_case(session, actor, case, status="resolved", resolution=resolution)


def dismiss_case(session: Session, actor: User, case: ModerationCase, *, resolution: str) -> ModerationCase:
    return _close_case(session, actor, case, status="dismissed", resolution=resolution)


def create_restriction(
    session: Session,
    actor: User,
    case: ModerationCase,
    user: User,
    *,
    restriction_type: str,
    reason_code: str,
    expires_at: datetime.datetime,
    now: datetime.datetime | None = None,
) -> AccountRestriction:
    require_operator(session, actor)
    current = now or utcnow()
    if case.status != "resolved":
        raise ValueError("只能依据已确认违规的案件执行限制")
    if case.subject_user_id != user.id:
        raise ValueError("受限用户与案件对象不一致")
    if restriction_type not in RESTRICTION_TYPES:
        raise ValueError("限制类型不受支持")
    if _aware(expires_at) <= _aware(current):
        raise ValueError("限制结束时间必须晚于当前时间")
    restriction = AccountRestriction(
        case_id=case.id,
        user_id=user.id,
        restriction_type=restriction_type,
        reason_code=reason_code.strip()[:100] or case.reason_code,
        starts_at=current,
        expires_at=expires_at,
        created_by=actor.id,
    )
    session.add(restriction)
    session.flush()
    _audit(
        session,
        actor.id,
        "account_restriction.create",
        "account_restriction",
        restriction.id,
        {
            "case_id": case.id,
            "user_id": user.id,
            "restriction_type": restriction_type,
            "reason_code": restriction.reason_code,
            "expires_at": _aware(expires_at).isoformat(),
        },
    )
    return restriction


def has_active_restriction(
    session: Session,
    user_id: int,
    restriction_type: str | None = None,
    *,
    now: datetime.datetime | None = None,
) -> bool:
    current = now or utcnow()
    filters = [
        AccountRestriction.user_id == user_id,
        AccountRestriction.revoked_at.is_(None),
        AccountRestriction.starts_at <= current,
        AccountRestriction.expires_at > current,
    ]
    if restriction_type is not None:
        filters.append(
            AccountRestriction.restriction_type.in_((restriction_type, "all_interactions"))
        )
    return session.execute(select(AccountRestriction.id).where(*filters).limit(1)).first() is not None


def submit_appeal(
    session: Session,
    appellant: User,
    case: ModerationCase,
    *,
    statement: str,
) -> Appeal:
    if case.status != "resolved":
        raise ValueError("只有已确认违规的案件可以申诉")
    if case.subject_user_id != appellant.id:
        raise PermissionError("只能对涉及自己账号的处理提交申诉")
    if not statement.strip():
        raise ValueError("请填写申诉说明")
    existing = session.execute(
        select(Appeal).where(Appeal.case_id == case.id, Appeal.appellant_id == appellant.id)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("该处理已经提交过申诉")
    appeal = Appeal(
        case_id=case.id,
        appellant_id=appellant.id,
        statement=statement.strip()[:4000],
    )
    session.add(appeal)
    session.flush()
    _audit(
        session,
        appellant.id,
        "appeal.submit",
        "appeal",
        appeal.id,
        {"case_id": case.id, "status": "pending"},
    )
    return appeal


def list_appeals(
    session: Session,
    actor: User,
    *,
    page: int,
    page_size: int,
    operator_queue: bool = False,
    status: str = "pending",
) -> tuple[list[Appeal], int]:
    if operator_queue:
        require_operator(session, actor)
        filters = () if status == "all" else (Appeal.status == status,)
    else:
        filters = (Appeal.appellant_id == actor.id,)
    total = session.scalar(select(func.count()).select_from(Appeal).where(*filters)) or 0
    rows = session.execute(
        select(Appeal)
        .where(*filters)
        .order_by(Appeal.created_at.asc(), Appeal.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(rows), int(total)


def review_appeal(
    session: Session,
    actor: User,
    appeal: Appeal,
    *,
    outcome: str,
    resolution: str,
    now: datetime.datetime | None = None,
) -> Appeal:
    require_operator(session, actor)
    if appeal.status != "pending":
        raise ValueError("申诉已经处理")
    if outcome not in {"approved", "rejected"}:
        raise ValueError("申诉处理结果不正确")
    if not resolution.strip():
        raise ValueError("请填写申诉处理结论")
    current = now or utcnow()
    appeal.status = outcome
    appeal.resolution = resolution.strip()[:500]
    appeal.reviewed_by = actor.id
    appeal.reviewed_at = current
    if outcome == "approved":
        restrictions = session.execute(
            select(AccountRestriction).where(
                AccountRestriction.case_id == appeal.case_id,
                AccountRestriction.revoked_at.is_(None),
                AccountRestriction.expires_at > current,
            )
        ).scalars().all()
        for restriction in restrictions:
            restriction.revoked_at = current
            restriction.revoked_by = actor.id
            _audit(
                session,
                actor.id,
                "account_restriction.revoke",
                "account_restriction",
                restriction.id,
                {"case_id": appeal.case_id, "appeal_id": appeal.id},
            )
    _audit(
        session,
        actor.id,
        f"appeal.{'approve' if outcome == 'approved' else 'reject'}",
        "appeal",
        appeal.id,
        {"case_id": appeal.case_id, "status": outcome},
    )
    notify(
        session,
        user_id=appeal.appellant_id,
        event_type=f"moderation.appeal.{outcome}",
        title="申诉处理已完成",
        body="你的申诉已通过，相关限制已解除" if outcome == "approved" else "你的申诉未通过，原处理继续有效",
        target_type="appeal",
        target_id=str(appeal.id),
        dedupe_key=f"appeal:{appeal.id}:{outcome}",
    )
    return appeal


def report_to_dict(report: Report) -> dict[str, Any]:
    return {
        "id": str(report.id),
        "target_type": report.target_type,
        "target_id": report.target_id,
        "reason_code": report.reason_code,
        "description": report.description,
        "report_count": report.report_count,
        "status": report.status,
        "resolution": report.resolution,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "resolved_at": report.resolved_at.isoformat() if report.resolved_at else None,
    }


def event_to_dict(event: ModerationEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "surface": event.surface,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "actor_id": str(event.actor_id) if event.actor_id is not None else None,
        "action": event.action,
        "risk_level": event.risk_level,
        "rule_ids": event.rule_ids,
        "excerpt": event.excerpt,
        "source": event.source,
        "status": event.status,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def case_to_dict(case: ModerationCase) -> dict[str, Any]:
    return {
        "id": str(case.id),
        "event_id": str(case.event_id) if case.event_id is not None else None,
        "report_id": str(case.report_id) if case.report_id is not None else None,
        "target_type": case.target_type,
        "target_id": case.target_id,
        "subject_user_id": str(case.subject_user_id) if case.subject_user_id is not None else None,
        "status": case.status,
        "priority": case.priority,
        "reason_code": case.reason_code,
        "assigned_operator_id": (
            str(case.assigned_operator_id) if case.assigned_operator_id is not None else None
        ),
        "resolution": case.resolution,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
    }


def restriction_to_dict(restriction: AccountRestriction) -> dict[str, Any]:
    return {
        "id": str(restriction.id),
        "case_id": str(restriction.case_id),
        "user_id": str(restriction.user_id),
        "restriction_type": restriction.restriction_type,
        "reason_code": restriction.reason_code,
        "starts_at": restriction.starts_at.isoformat() if restriction.starts_at else None,
        "expires_at": restriction.expires_at.isoformat() if restriction.expires_at else None,
        "revoked_at": restriction.revoked_at.isoformat() if restriction.revoked_at else None,
    }


def appeal_to_dict(appeal: Appeal) -> dict[str, Any]:
    return {
        "id": str(appeal.id),
        "case_id": str(appeal.case_id),
        "appellant_id": str(appeal.appellant_id),
        "statement": appeal.statement,
        "status": appeal.status,
        "resolution": appeal.resolution,
        "reviewed_by": str(appeal.reviewed_by) if appeal.reviewed_by is not None else None,
        "created_at": appeal.created_at.isoformat() if appeal.created_at else None,
        "reviewed_at": appeal.reviewed_at.isoformat() if appeal.reviewed_at else None,
    }
