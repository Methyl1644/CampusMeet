"""申请工具：创建申请、查看申请、接受/拒绝申请"""
import json
import logging
from langchain.tools import tool
from sqlalchemy import select, desc
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.post import Post
from storage.database.models.application import Application
from storage.database.models.conversation import Conversation
from tools.auth_tools import _user_brief

logger = logging.getLogger(__name__)


def _application_to_dict(app: Application, applicant: User | None = None) -> dict:
    data = {
        "id": str(app.id),
        "post_id": str(app.post_id),
        "applicant_id": str(app.applicant_id),
        "role_wanted": app.role_wanted,
        "experience": app.experience,
        "available_time": app.available_time,
        "reason": app.reason,
        "questions": app.questions or [],
        "status": app.status,
        "created_at": app.created_at.isoformat() if app.created_at else None,
    }
    if applicant:
        data["applicant"] = _user_brief(applicant)
    return data


@tool
def create_application(
    user_id: str,
    post_id: str,
    role_wanted: str,
    experience: str,
    available_time: str,
    reason: str,
    questions: str = "",
) -> str:
    """申请加入队伍。user_id 为申请者ID，post_id 为帖子ID，role_wanted 为期望角色，experience 为经验描述，available_time 为可用时间，reason 为申请原因，questions 为想问的问题(逗号分隔)。"""
    ctx = request_context.get() or new_context(method="create_application")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            pid = int(post_id)
            user = session.execute(select(User).where(User.id == uid)).scalar_one_or_none()
            if not user:
                return json.dumps({"success": False, "message": "用户不存在"}, ensure_ascii=False)
            if user.auth_status == "unverified":
                return json.dumps({"success": False, "message": "请先完成校园邮箱认证"}, ensure_ascii=False)

            post = session.execute(select(Post).where(Post.id == pid)).scalar_one_or_none()
            if not post:
                return json.dumps({"success": False, "message": "帖子不存在"}, ensure_ascii=False)
            if post.status != "recruiting":
                return json.dumps({"success": False, "message": "该帖子已停止招募"}, ensure_ascii=False)
            if post.author_id == uid:
                return json.dumps({"success": False, "message": "不能申请自己的帖子"}, ensure_ascii=False)

            q_list = [q.strip() for q in questions.split(",") if q.strip()] if questions else []
            app = Application(
                post_id=pid,
                applicant_id=uid,
                role_wanted=role_wanted,
                experience=experience,
                available_time=available_time,
                reason=reason,
                questions=q_list,
                status="pending",
            )
            session.add(app)
            session.commit()

            return json.dumps({
                "success": True,
                "application": _application_to_dict(app, user),
                "message": "申请已提交，等待发布者审核",
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"create_application error: {e}")
        return json.dumps({"success": False, "message": f"申请失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_applications(user_id: str, post_id: str = "") -> str:
    """查看收到的申请。user_id 为发布者ID，post_id 为帖子ID(可选，不传则查看所有帖子的申请)。"""
    ctx = request_context.get() or new_context(method="get_applications")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            query = (
                select(Application, Post)
                .join(Post, Application.post_id == Post.id)
                .where(Post.author_id == uid)
            )
            if post_id:
                query = query.where(Application.post_id == int(post_id))
            query = query.order_by(desc(Application.created_at))

            results = session.execute(query).all()
            apps = []
            for app, post in results:
                applicant = session.execute(select(User).where(User.id == app.applicant_id)).scalar_one_or_none()
                d = _application_to_dict(app, applicant)
                d["post_title"] = post.title
                apps.append(d)

            return json.dumps({"success": True, "list": apps, "total": len(apps)}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_applications error: {e}")
        return json.dumps({"success": False, "message": f"获取申请失败: {str(e)}"}, ensure_ascii=False)


@tool
def accept_application(user_id: str, application_id: str) -> str:
    """接受申请。user_id 为发布者ID，application_id 为申请ID。接受后创建临时聊天会话。"""
    ctx = request_context.get() or new_context(method="accept_application")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            aid = int(application_id)
            app = session.execute(select(Application).where(Application.id == aid)).scalar_one_or_none()
            if not app:
                return json.dumps({"success": False, "message": "申请不存在"}, ensure_ascii=False)

            post = session.execute(select(Post).where(Post.id == app.post_id)).scalar_one_or_none()
            if not post or post.author_id != uid:
                return json.dumps({"success": False, "message": "无权操作此申请"}, ensure_ascii=False)

            if app.status != "pending":
                return json.dumps({"success": False, "message": "该申请已处理"}, ensure_ascii=False)

            app.status = "accepted"

            # 创建临时会话
            conv = Conversation(
                post_id=app.post_id,
                post_author_id=uid,
                applicant_id=app.applicant_id,
                application_id=app.id,
                status="active",
                contact_unlocked=False,
            )
            session.add(conv)
            session.flush()

            session.commit()
            return json.dumps({
                "success": True,
                "conversation_id": str(conv.id),
                "message": "已接受申请，已创建临时聊天会话",
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"accept_application error: {e}")
        return json.dumps({"success": False, "message": f"接受申请失败: {str(e)}"}, ensure_ascii=False)


@tool
def reject_application(user_id: str, application_id: str) -> str:
    """拒绝申请。user_id 为发布者ID，application_id 为申请ID。"""
    ctx = request_context.get() or new_context(method="reject_application")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            aid = int(application_id)
            app = session.execute(select(Application).where(Application.id == aid)).scalar_one_or_none()
            if not app:
                return json.dumps({"success": False, "message": "申请不存在"}, ensure_ascii=False)

            post = session.execute(select(Post).where(Post.id == app.post_id)).scalar_one_or_none()
            if not post or post.author_id != uid:
                return json.dumps({"success": False, "message": "无权操作此申请"}, ensure_ascii=False)

            if app.status != "pending":
                return json.dumps({"success": False, "message": "该申请已处理"}, ensure_ascii=False)

            app.status = "rejected"
            session.commit()
            return json.dumps({"success": True, "message": "已拒绝该申请"}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"reject_application error: {e}")
        return json.dumps({"success": False, "message": f"拒绝申请失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_my_applications(user_id: str) -> str:
    """查看我提交的申请。user_id 为申请者ID。"""
    ctx = request_context.get() or new_context(method="get_my_applications")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            results = session.execute(
                select(Application, Post)
                .join(Post, Application.post_id == Post.id)
                .where(Application.applicant_id == uid)
                .order_by(desc(Application.created_at))
            ).all()

            apps = []
            for app, post in results:
                d = _application_to_dict(app)
                d["post_title"] = post.title
                d["post_status"] = post.status
                apps.append(d)

            return json.dumps({"success": True, "list": apps, "total": len(apps)}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_my_applications error: {e}")
        return json.dumps({"success": False, "message": f"获取申请失败: {str(e)}"}, ensure_ascii=False)
