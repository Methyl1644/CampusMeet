"""认证工具：验证码发送、注册、登录、邮箱认证、资料管理"""
import json
import datetime
import logging
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
        "major": user.major,
        "grade": user.grade,
    }


@tool
def register_auth_send_code(account: str) -> str:
    """发送验证码到手机号或邮箱。account 为手机号或邮箱地址。"""
    ctx = request_context.get() or new_context(method="register_auth_send_code")
    try:
        code = generate_verification_code()
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
        session = get_session()
        try:
            vc = VerificationCode(
                account=account,
                code=code,
                purpose="register",
                expires_at=expires_at,
            )
            session.add(vc)
            session.commit()
        finally:
            session.close()
        # 根据账号类型发送验证码
        if is_email(account):
            result = send_verification_email(account, code, "注册")
            return json.dumps({"sent": result["sent"], "code": result.get("code"), "message": result["message"]}, ensure_ascii=False)
        else:
            # 手机号：无短信网关，降级返回验证码
            return json.dumps({"sent": True, "code": code, "message": f"验证码已发送至 {account}（短信网关未配置，测试模式直接返回）"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"send_code error: {e}")
        return json.dumps({"sent": False, "message": f"发送验证码失败: {str(e)}"}, ensure_ascii=False)


@tool
def register_user(account: str, code: str, password: str, nickname: str, major: str, grade: str, skills: str, wechat: str = "") -> str:
    """注册新用户。account 为手机号或邮箱，code 为验证码，password 为密码，nickname 为昵称，major 为专业，grade 为年级，skills 为技能标签(逗号分隔)，wechat 为微信号(可选)。"""
    ctx = request_context.get() or new_context(method="register_user")
    try:
        session = get_session()
        try:
            # 验证验证码
            vc_result = session.execute(
                select(VerificationCode)
                .where(VerificationCode.account == account)
                .where(VerificationCode.used == False)
                .where(VerificationCode.expires_at > datetime.datetime.now(datetime.timezone.utc))
                .order_by(VerificationCode.created_at.desc())
                .limit(1)
            )
            vc = vc_result.scalar_one_or_none()
            if not vc or vc.code != code:
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
            is_email = "@" in account
            user = User(
                email=account if is_email else None,
                phone=account if not is_email else None,
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
def login_user(account: str, password: str) -> str:
    """用户登录。account 为手机号或邮箱，password 为密码。返回 JWT token 和用户信息。"""
    ctx = request_context.get() or new_context(method="login_user")
    try:
        session = get_session()
        try:
            result = session.execute(
                select(User).where((User.email == account) | (User.phone == account))
            )
            user = result.scalar_one_or_none()
            if not user:
                return json.dumps({"success": False, "message": "账号不存在"}, ensure_ascii=False)
            if not verify_password(password, user.password_hash):
                return json.dumps({"success": False, "message": "密码错误"}, ensure_ascii=False)

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
        session = get_session()
        try:
            uid = int(user_id)
            # 验证验证码
            vc_result = session.execute(
                select(VerificationCode)
                .where(VerificationCode.account == email)
                .where(VerificationCode.used == False)
                .where(VerificationCode.expires_at > datetime.datetime.now(datetime.timezone.utc))
                .order_by(VerificationCode.created_at.desc())
                .limit(1)
            )
            vc = vc_result.scalar_one_or_none()
            if not vc or vc.code != code:
                return json.dumps({"verified": False, "message": "验证码无效或已过期"}, ensure_ascii=False)

            user = session.execute(select(User).where(User.id == uid)).scalar_one_or_none()
            if not user:
                return json.dumps({"verified": False, "message": "用户不存在"}, ensure_ascii=False)

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
