from __future__ import annotations

import datetime
import os
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.database.models import AccountRequest, AuthSession, User
from services.auth_access import email_is_explicitly_allowlisted
from utils.auth import generate_token, hash_password, verify_password


ACCOUNT_REQUEST_TYPES = frozenset({"data_export", "account_deletion"})


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def aware(value: datetime.datetime) -> datetime.datetime:
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


def access_token_ttl_seconds() -> int:
    try:
        value = int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "86400"))
    except ValueError:
        return 86400
    return min(86400, max(900, value))


def validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 128:
        raise ValueError("密码长度需为 8 至 128 位")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("密码必须同时包含字母和数字")


def issue_access_token(
    session: Session,
    user_id: int,
    *,
    ttl_seconds: int | None = None,
) -> str:
    ttl = access_token_ttl_seconds() if ttl_seconds is None else min(86400, max(1, ttl_seconds))
    token_id = secrets.token_urlsafe(24)
    expires_at = utcnow() + datetime.timedelta(seconds=ttl)
    session.add(AuthSession(id=token_id, user_id=user_id, expires_at=expires_at))
    session.flush()
    return generate_token(user_id, expire_seconds=ttl, token_id=token_id)


def active_session(session: Session, token_id: str, user_id: int) -> AuthSession | None:
    item = session.get(AuthSession, token_id)
    if (
        item is None
        or item.user_id != user_id
        or item.revoked_at is not None
        or aware(item.expires_at) <= utcnow()
    ):
        return None
    return item


def promote_allowlisted_legacy_user(session: Session, user: User) -> bool:
    account = (user.email or user.verified_email or "").strip().casefold()
    if user.auth_status != "unverified" or not email_is_explicitly_allowlisted(account):
        return False
    user.auth_status = "verified"
    if not user.verified_email:
        email_owner = session.scalar(
            select(User.id).where(User.verified_email == account, User.id != user.id)
        )
        if email_owner is None:
            user.verified_email = account
    return True


def revoke_session(session: Session, token_id: str, *, reason: str) -> bool:
    item = session.get(AuthSession, token_id)
    if item is None or item.revoked_at is not None:
        return False
    item.revoked_at = utcnow()
    item.revoke_reason = reason[:80]
    return True


def revoke_user_sessions(session: Session, user_id: int, *, reason: str) -> int:
    rows = session.scalars(
        select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    ).all()
    now = utcnow()
    for item in rows:
        item.revoked_at = now
        item.revoke_reason = reason[:80]
    return len(rows)


def change_password(
    session: Session,
    user: User,
    *,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise PermissionError("当前密码不正确")
    validate_password(new_password)
    if verify_password(new_password, user.password_hash):
        raise ValueError("新密码不能与当前密码相同")
    user.password_hash = hash_password(new_password)
    revoke_user_sessions(session, user.id, reason="password_changed")


def reset_password(session: Session, user: User, *, new_password: str) -> None:
    validate_password(new_password)
    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    revoke_user_sessions(session, user.id, reason="password_reset")


def create_account_request(session: Session, user: User, request_type: str) -> AccountRequest:
    if request_type not in ACCOUNT_REQUEST_TYPES:
        raise ValueError("账号申请类型不受支持")
    existing = session.scalar(
        select(AccountRequest).where(
            AccountRequest.user_id == user.id,
            AccountRequest.request_type == request_type,
            AccountRequest.status == "pending",
        )
    )
    if existing is not None:
        return existing
    item = AccountRequest(user_id=user.id, request_type=request_type, status="pending")
    session.add(item)
    session.flush()
    if request_type == "account_deletion":
        user.account_status = "deletion_requested"
        user.deactivated_at = utcnow()
        revoke_user_sessions(session, user.id, reason="account_deletion_requested")
    return item


def account_request_to_dict(item: AccountRequest) -> dict:
    return {
        "id": str(item.id),
        "request_type": item.request_type,
        "status": item.status,
        "result_metadata": item.result_metadata or {},
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }
