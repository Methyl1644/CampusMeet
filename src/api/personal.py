from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api.common import api_ok, current_user_id
from api.schemas.personal import ProfilePatchRequest, SettingsPatchRequest
from services.onboarding import (
    profile_settings_to_dict,
    update_profile_fields,
    update_settings,
)
from services.personal_area import (
    list_personal_activities,
    list_personal_groups,
    public_profile,
)
from storage.database.db import get_session
from storage.database.models import User


router = APIRouter(tags=["personal"])


def _user_or_unauthorized(session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None or user.account_status != "active":
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return user


@router.get("/me/activities")
def activities(
    view: Literal["attending", "saved", "past"] = "attending",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=40),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = _user_or_unauthorized(session, int(user_id))
        return api_ok(
            list_personal_activities(
                session, user.id, view=view, page=page, page_size=page_size
            )
        )
    finally:
        session.close()


@router.get("/me/groups")
def groups(
    view: Literal["joined", "pending", "saved", "archived"] = "joined",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=40),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = _user_or_unauthorized(session, int(user_id))
        return api_ok(
            list_personal_groups(
                session, user.id, view=view, page=page, page_size=page_size
            )
        )
    finally:
        session.close()


@router.get("/profiles/{profile_user_id}", response_model_exclude_none=True)
def profile(
    profile_user_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        viewer = _user_or_unauthorized(session, int(user_id))
        profile_user = session.get(User, profile_user_id)
        if profile_user is None or profile_user.account_status != "active":
            raise HTTPException(status_code=404, detail="用户不存在")
        return api_ok(public_profile(session, profile_user, viewer.id))
    finally:
        session.close()


@router.patch("/me/profile")
def patch_profile(
    body: ProfilePatchRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = _user_or_unauthorized(session, int(user_id))
        try:
            data = update_profile_fields(user, body.model_dump(exclude_unset=True))
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return api_ok(data)
    finally:
        session.close()


@router.get("/me/settings")
def settings(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        user = _user_or_unauthorized(session, int(user_id))
        return api_ok(profile_settings_to_dict(user))
    finally:
        session.close()


@router.patch("/me/settings")
def patch_settings(
    body: SettingsPatchRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = _user_or_unauthorized(session, int(user_id))
        try:
            data = update_settings(user, body.model_dump(exclude_unset=True))
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return api_ok(data)
    finally:
        session.close()
