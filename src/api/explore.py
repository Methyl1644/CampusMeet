from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.common import api_ok, current_user_id
from api.schemas.explore import (
    ExploreActivityDetailResponse,
    ExploreActivityListResponse,
    ExploreGroupDetailResponse,
    ExploreGroupListResponse,
)
from services.explore import (
    get_activity_detail,
    get_group_detail,
    list_activities,
    list_groups,
)
from storage.database.db import get_session
from storage.database.models import User


router = APIRouter(prefix="/explore", tags=["explore"])


def _session_and_user(user_id: str):
    session = get_session()
    user = session.get(User, int(user_id))
    if user is None:
        session.close()
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return session, user


@router.get("/activities", response_model=ExploreActivityListResponse)
def activities(
    q: str = Query(default="", max_length=80),
    tag_ids: str = Query(default="", max_length=800),
    date_filter: str = Query(default="", alias="date", max_length=40),
    status: str = Query(default="active", max_length=40),
    type_filter: str = Query(default="", alias="type", max_length=40),
    campus: str = Query(default="", max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=40),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _session_and_user(user_id)
    try:
        return api_ok(
            list_activities(
                session,
                user.id,
                q=q,
                tag_ids=tag_ids,
                date_filter=date_filter,
                status=status,
                type_filter=type_filter,
                campus=campus,
                page=page,
                page_size=page_size,
            )
        )
    finally:
        session.close()


@router.get("/activities/{topic_id}", response_model=ExploreActivityDetailResponse)
def activity_detail(
    topic_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _session_and_user(user_id)
    try:
        detail = get_activity_detail(session, topic_id, user.id)
        if detail is None:
            raise HTTPException(status_code=404, detail="活动不存在")
        return api_ok(detail)
    finally:
        session.close()


@router.get("/groups", response_model=ExploreGroupListResponse)
def groups(
    q: str = Query(default="", max_length=80),
    tag_ids: str = Query(default="", max_length=800),
    date_filter: str = Query(default="", alias="date", max_length=40),
    status: str = Query(default="", max_length=40),
    type_filter: str = Query(default="", alias="type", max_length=40),
    campus: str = Query(default="", max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=40),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _session_and_user(user_id)
    try:
        return api_ok(
            list_groups(
                session,
                user.id,
                q=q,
                tag_ids=tag_ids,
                date_filter=date_filter,
                status=status,
                type_filter=type_filter,
                campus=campus,
                page=page,
                page_size=page_size,
            )
        )
    finally:
        session.close()


@router.get("/groups/{post_id}", response_model=ExploreGroupDetailResponse)
def group_detail(
    post_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _session_and_user(user_id)
    try:
        detail = get_group_detail(session, post_id, user.id)
        if detail is None:
            raise HTTPException(status_code=404, detail="组队不存在")
        return api_ok(detail)
    finally:
        session.close()
