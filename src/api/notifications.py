from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.common import api_ok, current_user_id
from services.notifications import (
    list_notifications,
    mark_all_read,
    mark_read,
    notification_to_dict,
    unread_count,
)
from storage.database.db import get_session


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_items(
    page: int = 1,
    page_size: int = 20,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        items, total = list_notifications(
            session, int(user_id), page=page, page_size=page_size
        )
        return api_ok(
            {
                "list": [notification_to_dict(item) for item in items],
                "total": total,
                "page": max(1, page),
                "page_size": min(100, max(1, page_size)),
                "pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
            }
        )
    finally:
        session.close()


@router.get("/unread-count")
def count_unread(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        return api_ok({"count": unread_count(session, int(user_id))})
    finally:
        session.close()


@router.post("/read-all")
def read_all(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        count = mark_all_read(session, int(user_id))
        session.commit()
        return api_ok({"updated": count})
    finally:
        session.close()


@router.post("/{notification_id}/read")
def read(notification_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        try:
            item = mark_read(session, int(user_id), notification_id)
            session.commit()
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return api_ok(notification_to_dict(item))
    finally:
        session.close()
