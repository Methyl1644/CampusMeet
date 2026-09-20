from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.common import api_ok, current_user_id
from api.schemas.uploads import UploadAttachRequest, UploadCompleteRequest, UploadCreateRequest
from services.rate_limit import upload_ticket_limiter
from services.uploads import (
    attach_public_upload,
    complete_upload,
    create_upload,
    get_upload_storage,
    reviewer_download_url,
)
from storage.database.db import get_session
from storage.database.models import User


router = APIRouter(prefix="/uploads", tags=["uploads"])


def _storage():
    try:
        return get_upload_storage()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("")
def start_upload(
    body: UploadCreateRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        if not upload_ticket_limiter.allow(str(user.id)):
            raise HTTPException(
                status_code=429,
                detail="上传请求过于频繁，请稍后再试",
                headers={"Retry-After": str(upload_ticket_limiter.retry_after_seconds(str(user.id)))},
            )
        try:
            record, instruction = create_upload(
                session,
                _storage(),
                user,
                **body.model_dump(),
            )
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return api_ok(
            {
                "upload_id": record.id,
                "purpose": record.purpose,
                "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                "upload": instruction,
            },
            "上传凭证已创建",
        )
    finally:
        session.close()


@router.post("/{upload_id}/complete")
def finish_upload(
    upload_id: str,
    body: UploadCompleteRequest | None = None,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        try:
            claimed = body.model_dump(exclude_none=True) if body is not None else {}
            record = complete_upload(session, _storage(), user, upload_id, claimed=claimed)
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            session.rollback()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return api_ok(
            {
                "upload_id": record.id,
                "purpose": record.purpose,
                "status": record.status,
                "reference": f"upload:{record.id}",
            },
            "上传已校验",
        )
    finally:
        session.close()


@router.get("/{upload_id}/review-url")
def review_url(upload_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        reviewer = session.get(User, int(user_id))
        if not reviewer:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        try:
            url = reviewer_download_url(session, _storage(), reviewer, upload_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return api_ok({"url": url, "expires_in": 300})
    finally:
        session.close()


@router.post("/{upload_id}/attach")
def attach_upload(
    upload_id: str,
    body: UploadAttachRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        actor = session.get(User, int(user_id))
        if not actor:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        try:
            record = attach_public_upload(
                session,
                _storage(),
                actor,
                upload_id,
                target_id=body.target_id,
            )
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            session.rollback()
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return api_ok(
            {
                "upload_id": record.id,
                "purpose": record.purpose,
                "status": record.status,
                "target_id": record.attached_to_id,
            },
            "媒体已绑定",
        )
    finally:
        session.close()
