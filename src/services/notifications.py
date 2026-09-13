from __future__ import annotations

import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from storage.database.models import Notification


def notify(
    session: Session,
    *,
    user_id: int,
    event_type: str,
    title: str,
    body: str,
    target_type: str | None,
    target_id: str | None,
    dedupe_key: str,
) -> Notification:
    existing = session.execute(
        select(Notification).where(Notification.dedupe_key == dedupe_key)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    item = Notification(
        user_id=user_id,
        event_type=event_type[:100],
        title=title.strip()[:120],
        body=body.strip()[:500],
        target_type=target_type[:80] if target_type else None,
        target_id=str(target_id)[:120] if target_id is not None else None,
        dedupe_key=dedupe_key[:200],
    )
    session.add(item)
    session.flush()
    return item


def list_notifications(
    session: Session,
    user_id: int,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Notification], int]:
    page = max(1, page)
    page_size = min(40, max(1, page_size))
    total = session.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
    ) or 0
    items = session.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    return list(items), int(total)


def unread_count(session: Session, user_id: int) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )


def mark_read(session: Session, user_id: int, notification_id: int) -> Notification:
    item = session.get(Notification, notification_id)
    if item is None or item.user_id != user_id:
        raise ValueError("通知不存在")
    if item.read_at is None:
        item.read_at = datetime.datetime.now(datetime.timezone.utc)
    return item


def mark_all_read(session: Session, user_id: int) -> int:
    result = session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=datetime.datetime.now(datetime.timezone.utc))
    )
    return int(result.rowcount or 0)


def notification_to_dict(item: Notification) -> dict:
    read_at = item.read_at
    if read_at is not None and read_at.tzinfo is None:
        read_at = read_at.replace(tzinfo=datetime.timezone.utc)
    created_at = item.created_at
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=datetime.timezone.utc)
    return {
        "id": str(item.id),
        "event_type": item.event_type,
        "title": item.title,
        "body": item.body,
        "target_type": item.target_type,
        "target_id": item.target_id,
        "read_at": read_at.isoformat() if read_at else None,
        "created_at": created_at.isoformat() if created_at else None,
    }
