"""认证工具：验证码发送、注册、登录、邮箱认证、资料管理"""
import json
import datetime
import hashlib
import hmac
import logging
import os
import re
from langchain.tools import tool
from sqlalchemy import select, update
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.verification_code import VerificationCode
from utils.auth import hash_password, verify_password, generate_token, generate_verification_code
from utils.email_sender import send_verification_email, is_email

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 10
CODE_RESEND_COOLDOWN_SECONDS = 60
MAX_CODE_ATTEMPTS = 5
MAX_PASSWORD_ATTEMPTS = 5
PASSWORD_LOCK_MINUTES = 15
ALLOWED_CODE_PURPOSES = {"register", "login", "campus_verify"}
PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")


def _is_campus_email(email: str) -> bool:
    if not is_email(email):
        return False
    domain = email.rsplit("@", 1)[1].strip().lower().rstrip(".")
    allowed_domains = {
        item.strip().lower().rstrip(".")
        for item in os.getenv("CAMPUS_EMAIL_DOMAINS", "nju.edu.cn").split(",")
        if item.strip()
    }
    return any(
        domain == allowed or domain.endswith(f".{allowed}")
        for allowed in allowed_domains
    )


def _is_test_mode() -> bool:
    configured = os.getenv("AUTH_TEST_MODE", "").strip().lower()
    if configured:
        return configured in {"1", "true", "yes", "on"}
    database_url = os.getenv("DATABASE_URL", "") or os.getenv("PGDATABASE_URL", "")
    return not database_url or database_url.startswith("sqlite:")


def _code_response(code: str, message: str, retry_after: int, reused: bool) -> str:
    payload = {
        "sent": True,
        "message": message,
        "retry_after_seconds": retry_after,
        "reused": reused,
        "test_mode": _is_test_mode(),
    }
    if payload["test_mode"]:
        payload["code"] = code
    return json.dumps(payload, ensure_ascii=False)


def _code_digest(account: str, purpose: str, code: str) -> str:
    secret = os.getenv("OTP_HASH_SECRET") or os.getenv("JWT_SECRET") or "campusmate-local-otp"
    value = f"{account}:{purpose}:{code}".encode("utf-8")
    return "sha256$" + hmac.new(secret.encode("utf-8"), value, hashlib.sha256).hexdigest()


def _stored_code(account: str, purpose: str, code: str) -> str:
    return code if _is_test_mode() else _code_digest(account, purpose, code)


def _code_matches(vc: VerificationCode, submitted: str) -> bool:
    if vc.code.startswith("sha256$"):
        expected = _code_digest(vc.account, vc.purpose, submitted)
        return hmac.compare_digest(vc.code, expected)
    return hmac.compare_digest(vc.code, submitted)


def _verify_code(session, account: str, purpose: str, submitted: str) -> VerificationCode | None:
    vc = session.execute(
        select(VerificationCode)
        .where(VerificationCode.account == account)
        .where(VerificationCode.purpose == purpose)
        .where(VerificationCode.used == False)
        .where(VerificationCode.expires_at > datetime.datetime.now(datetime.timezone.utc))
        .order_by(VerificationCode.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not vc:
        return None
    if _code_matches(vc, submitted):
        return vc
    vc.attempts = (vc.attempts or 0) + 1
    if vc.attempts >= MAX_CODE_ATTEMPTS:
        vc.used = True
    session.commit()
    return None


def _seconds_since(value: datetime.datetime, now: datetime.datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return max(0, int((now - value).total_seconds()))


def _invalidate_verification_code(verification_code_id: int) -> None:
    session = get_session()
    try:
        verification_code = session.get(VerificationCode, verification_code_id)
        if verification_code:
            verification_code.used = True
            session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to invalidate an undelivered verification code")
    finally:
        session.close()


def _user_to_dict(user: User) -> dict:
    """将 User 对象转为字典"""
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "wechat": user.wechat,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "major": user.major,
        "grade": user.grade,
        "skills": user.skills or [],
        "auth_status": user.auth_status,
        "site_role": user.site_role,
        "verified_email": user.verified_email,
        "post_count": user.post_count,
        "team_count": user.team_count,
    }


def _user_brief(user: User) -> dict:
    """用户简要信息"""
    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "avatar": user.avatar,
        "auth_status": user.auth_status,
        "site_role": user.site_role,
        "major": user.major,
        "grade": user.grade,
    }


@tool
def register_auth_send_code(account: str, purpose: str = "register") -> str:
    """发送验证码到手机号或邮箱。purpose 为 register、login 或 campus_verify。"""
    ctx = request_context.get() or new_context(method="register_auth_send_code")
    try:
        account = account.strip().lower() if is_email(account) else account.strip()
        if not (is_email(account) or PHONE_PATTERN.fullmatch(account)):
            return json.dumps({"sent": False, "message": "请输入正确的手机号或邮箱"}, ensure_ascii=False)
        if purpose not in ALLOWED_CODE_PURPOSES:
            return json.dumps({"sent": False, "message": "不支持的验证码用途"}, ensure_ascii=False)
        if purpose == "campus_verify" and not _is_campus_email(account):
            return json.dumps(
                {"sent": False, "message": "请使用南京大学校园邮箱完成认证"},
                ensure_ascii=False,
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        session = get_session()
        try:
            active = session.execute(
                select(VerificationCode)
                .where(VerificationCode.account == account)
                .where(VerificationCode.purpose == purpose)
                .where(VerificationCode.used == False)
                .where(VerificationCode.expires_at > now)
                .order_by(VerificationCode.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if active and active.created_at is not None:
                age = _seconds_since(active.created_at, now)
                if age < CODE_RESEND_COOLDOWN_SECONDS:
                    retry_after = CODE_RESEND_COOLDOWN_SECONDS - age
                    return _code_response(
                        active.code,
                        "验证码仍然有效，请使用上一条验证码",
                        retry_after,
                        True,
                    )

            if not is_email(account) and not _is_test_mode():
                return json.dumps(
                    {"sent": False, "message": "短信服务尚未配置，请改用邮箱注册或联系管理员"},
                    ensure_ascii=False,
                )

            code = generate_verification_code()
            expires_at = now + datetime.timedelta(minutes=CODE_TTL_MINUTES)
            vc = VerificationCode(
                account=account,
                code=_stored_code(account, purpose, code),
                purpose=purpose,
                expires_at=expires_at,
            )
            session.add(vc)
            session.commit()
            verification_code_id = vc.id
        finally:
            session.close()

        # 根据账号类型发送验证码
        if is_email(account):
            purpose_label = {"register": "注册", "login": "登录", "campus_verify": "校园认证"}[purpose]
            result = send_verification_email(account, code, purpose_label)
            if result.get("code") and not _is_test_mode():
                _invalidate_verification_code(verification_code_id)
                return json.dumps(
                    {"sent": False, "message": "验证码邮件发送失败，请稍后重试或联系管理员"},
                    ensure_ascii=False,
                )
            if not result["sent"]:
                _invalidate_verification_code(verification_code_id)
                return json.dumps(result, ensure_ascii=False)
            message = result["message"]
        else:
            message = f"验证码已生成至 {account}（本地测试模式）"

        return _code_response(code, message, CODE_RESEND_COOLDOWN_SECONDS, False)
    except Exception as e:
        logger.error(f"send_code error: {e}")
        return json.dumps({"sent": False, "message": f"发送验证码失败: {str(e)}"}, ensure_ascii=False)


@tool
def register_user(account: str, code: str, password: str, nickname: str, major: str, grade: str, skills: str, wechat: str = "") -> str:
    """注册新用户。account 为手机号或邮箱，code 为验证码，password 为密码，nickname 为昵称，major 为专业，grade 为年级，skills 为技能标签(逗号分隔)，wechat 为微信号(可选)。"""
    ctx = request_context.get() or new_context(method="register_user")
    try:
        account = account.strip().lower() if is_email(account) else account.strip()
        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            return json.dumps(
                {"success": False, "message": "密码至少 8 位，并同时包含字母和数字"},
                ensure_ascii=False,
            )
        session = get_session()
        try:
            # 验证验证码
            vc = _verify_code(session, account, "register", code)
            if not vc:
                return json.dumps({"success": False, "message": "验证码无效或已过期"}, ensure_ascii=False)

            # 检查账号是否已存在
            existing = session.execute(
                select(User).where((User.email == account) | (User.phone == account))
            ).scalar_one_or_none()
            if existing:
                return json.dumps({"success": False, "message": "该账号已注册"}, ensure_ascii=False)

            # 解析技能
            skill_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else []

            # 创建用户
            account_is_email = is_email(account)
            user = User(
                email=account if account_is_email else None,
                phone=account if not account_is_email else None,
                wechat=wechat if wechat else None,
                password_hash=hash_password(password),
                nickname=nickname,
                major=major,
                grade=grade,
                skills=skill_list,
                auth_status="unverified",
            )
            session.add(user)
            session.flush()

            # 标记验证码已使用
            vc.used = True

            # 生成 token
            token = generate_token(user.id)
            session.commit()

            return json.dumps({
                "success": True,
                "token": token,
                "user": _user_to_dict(user),
                "message": "注册成功，请完成校园邮箱认证以获取完整权限"
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"register_user error: {e}")
        return json.dumps({"success": False, "message": f"注册失败: {str(e)}"}, ensure_ascii=False)


@tool
def login_user(account: str, password: str = "", code: str = "") -> str:
    """用户登录。密码和登录验证码二选一，验证码只能使用一次。"""
    ctx = request_context.get() or new_context(method="login_user")
    try:
        account = account.strip().lower() if is_email(account) else account.strip()
        session = get_session()
        try:
            result = session.execute(
                select(User).where((User.email == account) | (User.phone == account))
            )
            user = result.scalar_one_or_none()
            if not user:
                return json.dumps({"success": False, "message": "账号不存在"}, ensure_ascii=False)

            if password:
                now = datetime.datetime.now(datetime.timezone.utc)
                locked_until = user.locked_until
                if locked_until and locked_until.tzinfo is None:
                    locked_until = locked_until.replace(tzinfo=datetime.timezone.utc)
                if locked_until and locked_until > now:
                    return json.dumps(
                        {"success": False, "message": "登录尝试过多，请稍后再试"},
                        ensure_ascii=False,
                    )
                if not verify_password(password, user.password_hash):
                    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                    if user.failed_login_attempts >= MAX_PASSWORD_ATTEMPTS:
                        user.failed_login_attempts = 0
                        user.locked_until = now + datetime.timedelta(minutes=PASSWORD_LOCK_MINUTES)
                    session.commit()
                    return json.dumps({"success": False, "message": "密码错误"}, ensure_ascii=False)
                user.failed_login_attempts = 0
                user.locked_until = None
                session.commit()
            elif code:
                vc = _verify_code(session, account, "login", code)
                if not vc:
                    return json.dumps({"success": False, "message": "验证码无效或已过期"}, ensure_ascii=False)
                vc.used = True
                session.commit()
            else:
                return json.dumps({"success": False, "message": "请输入密码或验证码"}, ensure_ascii=False)

            token = generate_token(user.id)
            return json.dumps({
                "success": True,
                "token": token,
                "user": _user_to_dict(user),
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"login_user error: {e}")
        return json.dumps({"success": False, "message": f"登录失败: {str(e)}"}, ensure_ascii=False)


@tool
def verify_campus_email(user_id: str, email: str, code: str) -> str:
    """校园邮箱认证。user_id 为用户ID，email 为校园邮箱地址，code 为验证码。认证后用户获得发帖和申请权限。"""
    ctx = request_context.get() or new_context(method="verify_campus_email")
    try:
        email = email.strip().lower()
        if not _is_campus_email(email):
            return json.dumps(
                {"verified": False, "message": "请使用南京大学校园邮箱完成认证"},
                ensure_ascii=False,
            )
        session = get_session()
        try:
            uid = int(user_id)
            # 验证验证码
            vc = _verify_code(session, email, "campus_verify", code)
            if not vc:
                return json.dumps({"verified": False, "message": "验证码无效或已过期"}, ensure_ascii=False)

            user = session.execute(select(User).where(User.id == uid)).scalar_one_or_none()
            if not user:
                return json.dumps({"verified": False, "message": "用户不存在"}, ensure_ascii=False)

            existing_binding = session.execute(
                select(User).where(
                    User.verified_email == email,
                    User.id != uid,
                )
            ).scalar_one_or_none()
            if existing_binding:
                return json.dumps(
                    {"verified": False, "message": "该校园邮箱已绑定其他账号"},
                    ensure_ascii=False,
                )

            user.auth_status = "verified"
            user.verified_email = email
            vc.used = True
            session.commit()

            return json.dumps({
                "verified": True,
                "message": "校园邮箱认证成功，您现在可以发帖和申请加入队伍了",
                "user": _user_to_dict(user),
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"verify_campus_email error: {e}")
        return json.dumps({"verified": False, "message": f"认证失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_user_profile(user_id: str) -> str:
    """获取用户个人资料。user_id 为用户ID。"""
    ctx = request_context.get() or new_context(method="get_user_profile")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            user = session.execute(select(User).where(User.id == uid)).scalar_one_or_none()
            if not user:
                return json.dumps({"success": False, "message": "用户不存在"}, ensure_ascii=False)
            return json.dumps({"success": True, "user": _user_to_dict(user)}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_user_profile error: {e}")
        return json.dumps({"success": False, "message": f"获取资料失败: {str(e)}"}, ensure_ascii=False)


@tool
def update_user_profile(user_id: str, nickname: str = "", major: str = "", grade: str = "", skills: str = "", wechat: str = "") -> str:
    """更新用户资料。user_id 为用户ID，nickname 为昵称，major 为专业，grade 为年级，skills 为技能标签(逗号分隔)，wechat 为微信号。留空的字段不更新。"""
    ctx = request_context.get() or new_context(method="update_user_profile")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            user = session.execute(select(User).where(User.id == uid)).scalar_one_or_none()
            if not user:
                return json.dumps({"success": False, "message": "用户不存在"}, ensure_ascii=False)

            if nickname:
                user.nickname = nickname
            if major:
                user.major = major
            if grade:
                user.grade = grade
            if skills:
                user.skills = [s.strip() for s in skills.split(",") if s.strip()]
            if wechat:
                user.wechat = wechat

            session.commit()
            return json.dumps({"success": True, "user": _user_to_dict(user), "message": "资料更新成功"}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"update_user_profile error: {e}")
        return json.dumps({"success": False, "message": f"更新失败: {str(e)}"}, ensure_ascii=False)
