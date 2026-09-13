"""申请工具：创建申请、查看申请、接受/拒绝申请"""
import json
import logging
from dataclasses import asdict
from langchain.tools import tool
from sqlalchemy import select, desc
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.post import Post
from storage.database.models.application import Application
from storage.database.models.conversation import Conversation
from storage.database.models.content import AuditLog
from services.content_moderation import ModerationContext, moderate_content
from services.abuse_monitoring import check_and_record
from services.moderation_cases import (
    create_case_from_event,
    has_active_restriction,
    record_moderation_event,
    users_are_blocked,
)
from services.permissions import can_manage_post
from services.collaboration_lifecycle import withdraw_application as withdraw_record
from services.notifications import notify
from services.participation import ParticipationError, validate_application_join
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
            if post.author_id == uid:
                return json.dumps({"success": False, "message": "不能申请自己的帖子"}, ensure_ascii=False)
            try:
                validate_application_join(session, post, user)
            except ParticipationError as exc:
                return json.dumps(
                    {"success": False, "error_code": exc.code, "message": exc.message},
                    ensure_ascii=False,
                )
            if has_active_restriction(session, uid, "applications"):
                return json.dumps(
                    {"success": False, "message": "当前账号处于申请限制期，暂时不能提交申请"},
                    ensure_ascii=False,
                )
            if users_are_blocked(session, uid, post.author_id):
                return json.dumps(
                    {"success": False, "message": "你与帖子发布者之间存在屏蔽关系，无法提交申请"},
                    ensure_ascii=False,
                )

            q_list = [q.strip() for q in questions.split(",") if q.strip()] if questions else []
            abuse = check_and_record(
                session,
                user_id=uid,
                event_type="application",
                target_id=f"post:{pid}",
                content=" ".join([role_wanted, experience, available_time, reason, *q_list]),
            )
            if abuse.action in {"cooldown", "review"}:
                session.commit()
                return json.dumps(
                    {
                        "success": False,
                        "message": "操作过于频繁，请稍后再提交申请",
                        "retry_after_seconds": abuse.retry_after_seconds,
                    },
                    ensure_ascii=False,
                )
            moderation = moderate_content(
                reason,
                ModerationContext(
                    surface="application",
                    user_id=user_id,
                    structured_fields={
                        "role_wanted": role_wanted,
                        "experience": experience,
                        "available_time": available_time,
                        "questions": q_list,
                    },
                ),
            )
            if moderation.action != "allow":
                event = record_moderation_event(
                    session,
                    actor_id=uid,
                    surface="application",
                    target_type="user",
                    target_id=str(uid),
                    action=moderation.action,
                    risk_level=moderation.risk_level,
                    rule_ids=moderation.rule_ids,
                    raw_excerpt=" ".join(
                        [role_wanted, experience, available_time, reason, *q_list]
                    ),
                    source="rules",
                )
                if moderation.action in {"review", "block"}:
                    create_case_from_event(
                        session,
                        event,
                        subject_user_id=uid,
                        reason_code=moderation.rule_ids[0] if moderation.rule_ids else "content_risk",
                        priority="high" if moderation.action == "block" else "normal",
                    )
                session.commit()
                logger.info(
                    "Application moderation rejected user=%s post=%s action=%s rules=%s",
                    user_id,
                    post_id,
                    moderation.action,
                    moderation.rule_ids,
                )
                return json.dumps(
                    {
                        "success": False,
                        "message": moderation.user_message,
                        "moderation": asdict(moderation),
                    },
                    ensure_ascii=False,
                )
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
            session.flush()
            notify(
                session,
                user_id=post.author_id,
                event_type="application.created",
                title="收到新申请",
                body=f"{user.nickname} 申请加入「{post.title}」",
                target_type="application",
                target_id=str(app.id),
                dedupe_key=f"application:{app.id}:created",
            )
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
def get_applications(
    user_id: str,
    post_id: str = "",
    page: int = 1,
    page_size: int = 20,
) -> str:
    """查看收到的申请。user_id 为发布者ID，post_id 为帖子ID(可选，不传则查看所有帖子的申请)。"""
    ctx = request_context.get() or new_context(method="get_applications")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            user = session.get(User, uid)
            if not user:
                return json.dumps({"success": False, "message": "用户不存在"}, ensure_ascii=False)
            manageable_posts = [
                post.id
                for post in session.execute(select(Post)).scalars().all()
                if can_manage_post(session, user, post, "manage_applications")
            ]
            query = select(Application, Post).join(Post, Application.post_id == Post.id).where(Post.id.in_(manageable_posts))
            if post_id:
                query = query.where(Application.post_id == int(post_id))
            query = query.order_by(desc(Application.created_at))
            page = max(1, int(page))
            page_size = min(100, max(1, int(page_size)))
            total = len(session.execute(query).all())
            results = session.execute(
                query.offset((page - 1) * page_size).limit(page_size)
            ).all()
            apps = []
            for app, post in results:
                applicant = session.execute(select(User).where(User.id == app.applicant_id)).scalar_one_or_none()
                d = _application_to_dict(app, applicant)
                d["post_title"] = post.title
                apps.append(d)

            return json.dumps(
                {
                    "success": True,
                    "list": apps,
                    "total": total,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": total,
                        "pages": (total + page_size - 1) // page_size,
                    },
                },
                ensure_ascii=False,
            )
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
            user = session.get(User, uid)
            if not post or not user or not can_manage_post(session, user, post, "manage_applications"):
                return json.dumps({"success": False, "message": "无权操作此申请"}, ensure_ascii=False)

            if app.status != "pending":
                if app.status == "accepted":
                    existing = session.execute(
                        select(Conversation).where(Conversation.application_id == app.id)
                    ).scalar_one_or_none()
                    if existing:
                        return json.dumps(
                            {
                                "success": True,
                                "conversation_id": str(existing.id),
                                "message": "该申请已接受",
                            },
                            ensure_ascii=False,
                        )
                return json.dumps({"success": False, "message": "该申请已处理"}, ensure_ascii=False)

            applicant = session.get(User, app.applicant_id)
            if applicant is None:
                return json.dumps({"success": False, "message": "申请者不存在"}, ensure_ascii=False)
            try:
                validate_application_join(session, post, applicant)
            except ParticipationError as exc:
                return json.dumps(
                    {"success": False, "error_code": exc.code, "message": exc.message},
                    ensure_ascii=False,
                )
            if users_are_blocked(session, post.author_id, app.applicant_id):
                return json.dumps({"success": False, "message": "双方存在屏蔽关系，无法接受申请"}, ensure_ascii=False)

            app.status = "accepted"

            # 创建临时会话
            conv = Conversation(
                post_id=app.post_id,
                post_author_id=post.author_id,
                applicant_id=app.applicant_id,
                application_id=app.id,
                status="active",
                contact_unlocked=False,
            )
            session.add(conv)
            session.add(
                AuditLog(
                    user_id=uid,
                    action="application.accept",
                    target_type="application",
                    target_id=str(app.id),
                    detail=json.dumps({"post_id": post.id, "post_author_id": post.author_id}),
                )
            )
            session.flush()

            notify(
                session,
                user_id=app.applicant_id,
                event_type="application.accepted",
                title="申请已通过",
                body=f"你对「{post.title}」的申请已通过",
                target_type="conversation",
                target_id=str(conv.id),
                dedupe_key=f"application:{app.id}:accepted",
            )

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
            user = session.get(User, uid)
            if not post or not user or not can_manage_post(session, user, post, "manage_applications"):
                return json.dumps({"success": False, "message": "无权操作此申请"}, ensure_ascii=False)

            if app.status != "pending":
                return json.dumps({"success": False, "message": "该申请已处理"}, ensure_ascii=False)

            app.status = "rejected"
            notify(
                session,
                user_id=app.applicant_id,
                event_type="application.rejected",
                title="申请未通过",
                body=f"你对「{post.title}」的申请未通过",
                target_type="application",
                target_id=str(app.id),
                dedupe_key=f"application:{app.id}:rejected",
            )
            session.add(
                AuditLog(
                    user_id=uid,
                    action="application.reject",
                    target_type="application",
                    target_id=str(app.id),
                    detail=json.dumps({"post_id": post.id, "post_author_id": post.author_id}),
                )
            )
            session.commit()
            return json.dumps({"success": True, "message": "已拒绝该申请"}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"reject_application error: {e}")
        return json.dumps({"success": False, "message": f"拒绝申请失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_my_applications(user_id: str, page: int = 1, page_size: int = 20) -> str:
    """查看我提交的申请。user_id 为申请者ID。"""
    ctx = request_context.get() or new_context(method="get_my_applications")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            query = (
                select(Application, Post)
                .join(Post, Application.post_id == Post.id)
                .where(Application.applicant_id == uid)
                .order_by(desc(Application.created_at))
            )
            page = max(1, int(page))
            page_size = min(100, max(1, int(page_size)))
            total = len(session.execute(query).all())
            results = session.execute(
                query.offset((page - 1) * page_size).limit(page_size)
            ).all()

            apps = []
            for app, post in results:
                d = _application_to_dict(app)
                d["post_title"] = post.title
                d["post_status"] = post.status
                apps.append(d)

            return json.dumps(
                {
                    "success": True,
                    "list": apps,
                    "total": total,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": total,
                        "pages": (total + page_size - 1) // page_size,
                    },
                },
                ensure_ascii=False,
            )
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_my_applications error: {e}")
        return json.dumps({"success": False, "message": f"获取申请失败: {str(e)}"}, ensure_ascii=False)


@tool
def withdraw_application(user_id: str, application_id: str) -> str:
    """撤回待处理的申请。"""
    session = get_session()
    try:
        actor = session.get(User, int(user_id))
        application = session.get(Application, int(application_id))
        if not actor:
            return json.dumps({"success": False, "message": "用户不存在"}, ensure_ascii=False)
        if not application:
            return json.dumps({"success": False, "message": "申请不存在"}, ensure_ascii=False)
        try:
            withdraw_record(session, actor, application)
            session.commit()
        except (PermissionError, ValueError) as exc:
            session.rollback()
            return json.dumps({"success": False, "message": str(exc)}, ensure_ascii=False)
        return json.dumps(
            {"success": True, "application": _application_to_dict(application), "message": "申请已撤回"},
            ensure_ascii=False,
        )
    finally:
        session.close()
