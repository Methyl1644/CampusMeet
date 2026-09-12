from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select

from api.common import api_ok, current_user_id, invoke_tool, parse_tool_result, unwrap_data
from api.schemas.auth import (
    AccountDeactivateRequest,
    AccountRequestCreate,
    CampusEmailVerificationRequest,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    RegisterRequest,
    SendCodeRequest,
    ProfileUpdateRequest,
    OnboardingUpdateRequest,
)
from services.auth_lifecycle import (
    account_request_to_dict,
    change_password,
    create_account_request,
    reset_password,
    revoke_session,
    revoke_user_sessions,
    utcnow,
)
from services.identity import identity_summary
from services.onboarding import (
    complete_onboarding,
    onboarding_to_dict,
    update_onboarding,
)
from storage.database.db import get_session
from storage.database.models import AccountRequest, User
from tools.auth_tools import (
    _verify_code,
    get_user_profile,
    login_user,
    register_auth_send_code,
    register_user,
    update_user_profile,
    verify_campus_email,
)
from utils.auth import verify_password, verify_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-code")
def send_code(body: SendCodeRequest, request: Request) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            register_auth_send_code,
            {
                "account": body.account,
                "purpose": body.purpose,
                "network_identifier": request.client.host if request.client else "",
            },
        )
    )


@router.post("/register")
def register(body: RegisterRequest, request: Request) -> dict[str, Any]:
    raw = invoke_tool(
        register_user,
        {
            "account": body.account,
            "code": body.code,
            "password": body.password,
            "network_identifier": request.client.host if request.client else "",
        },
    )
    data = unwrap_data(raw)
    return {"code": 0, "message": data.get("message", "ok"), "data": {"token": data["token"], "user": data["user"]}}


@router.post("/login")
def login(body: LoginRequest, request: Request) -> dict[str, Any]:
    raw = invoke_tool(
        login_user,
        {
            "account": body.account,
            "password": body.password,
            "network_identifier": request.client.host if request.client else "",
        },
    )
    data = unwrap_data(raw)
    return {"code": 0, "message": "ok", "data": {"token": data["token"], "user": data["user"]}}


@router.post("/verify-email")
def verify_email(
    body: CampusEmailVerificationRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    body = body.model_dump() if isinstance(body, CampusEmailVerificationRequest) else body
    return parse_tool_result(
        invoke_tool(
            verify_campus_email,
            {"user_id": user_id, "email": body.get("email", ""), "code": body.get("code", "")},
        )
    )


@router.get("/profile")
def profile(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(get_user_profile, {"user_id": user_id}), "user")
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user and isinstance(result.get("data"), dict):
            result["data"]["identity"] = identity_summary(session, user)
        return result
    finally:
        session.close()


@router.patch("/profile")
def update_profile(body: ProfileUpdateRequest, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    body = body.model_dump() if isinstance(body, ProfileUpdateRequest) else body
    skills = body.get("skills") or ""
    raw = invoke_tool(
        update_user_profile,
        {
            "user_id": user_id,
            "nickname": body.get("nickname", ""),
            "major": body.get("major", ""),
            "grade": body.get("grade", ""),
            "skills": ",".join(skills) if isinstance(skills, list) else str(skills),
            "wechat": body.get("wechat", ""),
        },
    )
    return parse_tool_result(raw, "user")


@router.get("/onboarding")
def get_onboarding(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        return api_ok(onboarding_to_dict(user))
    finally:
        session.close()


@router.patch("/onboarding")
def patch_onboarding(
    body: OnboardingUpdateRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        try:
            data = update_onboarding(
                session,
                user,
                body.model_dump(exclude_unset=True),
            )
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        session.commit()
        return api_ok(data)
    finally:
        session.close()


@router.post("/onboarding/complete")
def finish_onboarding(
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        try:
            data = complete_onboarding(session, user)
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        session.commit()
        return api_ok(data)
    finally:
        session.close()


@router.post("/logout")
def logout(
    authorization: str | None = Header(default=None),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    token = authorization.split(" ", 1)[1].strip() if authorization else ""
    payload = verify_token(token)
    if not payload or str(payload.get("user_id")) != user_id:
        raise HTTPException(status_code=401, detail="登录状态已失效")
    session = get_session()
    try:
        revoke_session(session, str(payload["jti"]), reason="logout")
        session.commit()
        return api_ok(None, "已退出登录")
    finally:
        session.close()


@router.post("/change-password")
def change_account_password(
    body: PasswordChangeRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        try:
            change_password(
                session,
                user,
                current_password=body.current_password,
                new_password=body.new_password,
            )
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return api_ok(None, "密码已修改，请重新登录")
    finally:
        session.close()


@router.post("/reset-password")
def reset_account_password(body: PasswordResetRequest) -> dict[str, Any]:
    account = body.account.strip().casefold()
    session = get_session()
    try:
        code = _verify_code(session, account, "reset_password", body.code)
        user = session.scalar(select(User).where(User.email == account))
        if code is None or user is None:
            raise HTTPException(status_code=400, detail="验证码无效或已过期")
        try:
            reset_password(session, user, new_password=body.new_password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        session.commit()
        return api_ok(None, "密码已重置，请重新登录")
    finally:
        session.close()


@router.post("/deactivate")
def deactivate_account(
    body: AccountDeactivateRequest,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None or not verify_password(body.current_password, user.password_hash):
            raise HTTPException(status_code=403, detail="当前密码不正确")
        user.account_status = "deactivated"
        user.deactivated_at = utcnow()
        revoke_user_sessions(session, user.id, reason="account_deactivated")
        session.commit()
        return api_ok(None, "账号已停用")
    finally:
        session.close()


@router.post("/account-requests")
def request_account_action(
    body: AccountRequestCreate,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        item = create_account_request(session, user, body.request_type)
        session.commit()
        return api_ok(account_request_to_dict(item), "申请已提交")
    finally:
        session.close()


@router.get("/account-requests")
def my_account_requests(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session = get_session()
    try:
        filters = (AccountRequest.user_id == int(user_id),)
        total = int(session.scalar(select(func.count()).select_from(AccountRequest).where(*filters)) or 0)
        rows = session.scalars(
            select(AccountRequest)
            .where(*filters)
            .order_by(AccountRequest.created_at.desc(), AccountRequest.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return api_ok(
            {
                "list": [account_request_to_dict(item) for item in rows],
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }
        )
    finally:
        session.close()
