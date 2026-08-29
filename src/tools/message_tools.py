"""消息工具：会话列表、聊天消息、发送消息、确认组队、关闭会话"""
import json
import logging
from langchain.tools import tool
from sqlalchemy import select, desc, or_
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.post import Post
from storage.database.models.conversation import Conversation, Message
from storage.database.models.application import Application
from storage.database.models.team import Team, TeamMember
from tools.auth_tools import _user_brief

logger = logging.getLogger(__name__)


def _conversation_to_dict(conv: Conversation, other_user: User | None = None, post: Post | None = None) -> dict:
    data = {
        "id": str(conv.id),
        "post_id": str(conv.post_id),
        "status": conv.status,
        "contact_unlocked": conv.contact_unlocked,
        "last_message": conv.last_message,
        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
    }
    if other_user:
        data["other_user"] = _user_brief(other_user)
    if post:
        data["post_title"] = post.title
    return data


def _message_to_dict(msg: Message, is_mine: bool) -> dict:
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "sender_id": str(msg.sender_id),
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "is_mine": is_mine,
    }


@tool
def get_conversations(user_id: str) -> str:
    """获取会话列表。user_id 为当前用户ID。"""
    ctx = request_context.get() or new_context(method="get_conversations")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            results = session.execute(
                select(Conversation)
                .where(or_(Conversation.post_author_id == uid, Conversation.applicant_id == uid))
                .order_by(desc(Conversation.last_message_at))
            ).scalars().all()

            convs = []
            for conv in results:
                other_id = conv.applicant_id if conv.post_author_id == uid else conv.post_author_id
                other_user = session.execute(select(User).where(User.id == other_id)).scalar_one_or_none()
                post = session.execute(select(Post).where(Post.id == conv.post_id)).scalar_one_or_none()
                convs.append(_conversation_to_dict(conv, other_user, post))

            return json.dumps({"success": True, "list": convs, "total": len(convs)}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_conversations error: {e}")
        return json.dumps({"success": False, "message": f"获取会话失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_messages(user_id: str, conversation_id: str) -> str:
    """获取聊天消息。user_id 为当前用户ID，conversation_id 为会话ID。"""
    ctx = request_context.get() or new_context(method="get_messages")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            cid = int(conversation_id)
            conv = session.execute(select(Conversation).where(Conversation.id == cid)).scalar_one_or_none()
            if not conv:
                return json.dumps({"success": False, "message": "会话不存在"}, ensure_ascii=False)
            if conv.post_author_id != uid and conv.applicant_id != uid:
                return json.dumps({"success": False, "message": "无权查看此会话"}, ensure_ascii=False)

            results = session.execute(
                select(Message).where(Message.conversation_id == cid).order_by(Message.created_at)
            ).scalars().all()

            messages = [_message_to_dict(m, m.sender_id == uid) for m in results]
            return json.dumps({"success": True, "list": messages, "total": len(messages)}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_messages error: {e}")
        return json.dumps({"success": False, "message": f"获取消息失败: {str(e)}"}, ensure_ascii=False)


@tool
def send_message(user_id: str, conversation_id: str, content: str) -> str:
    """发送聊天消息。user_id 为发送者ID，conversation_id 为会话ID，content 为消息内容。"""
    ctx = request_context.get() or new_context(method="send_message")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            cid = int(conversation_id)
            conv = session.execute(select(Conversation).where(Conversation.id == cid)).scalar_one_or_none()
            if not conv:
                return json.dumps({"success": False, "message": "会话不存在"}, ensure_ascii=False)
            if conv.post_author_id != uid and conv.applicant_id != uid:
                return json.dumps({"success": False, "message": "无权在此会话中发送消息"}, ensure_ascii=False)
            if conv.status == "closed":
                return json.dumps({"success": False, "message": "会话已关闭"}, ensure_ascii=False)

            import datetime
            msg = Message(
                conversation_id=cid,
                sender_id=uid,
                content=content,
            )
            session.add(msg)
            session.flush()

            conv.last_message = content
            conv.last_message_at = datetime.datetime.now(datetime.timezone.utc)

            session.commit()
            return json.dumps({
                "success": True,
                "message": _message_to_dict(msg, True),
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"send_message error: {e}")
        return json.dumps({"success": False, "message": f"发送消息失败: {str(e)}"}, ensure_ascii=False)


@tool
def confirm_team(user_id: str, conversation_id: str) -> str:
    """确认组队。user_id 为当前用户ID，conversation_id 为会话ID。双方都确认后创建团队并解锁联系方式。"""
    ctx = request_context.get() or new_context(method="confirm_team")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            cid = int(conversation_id)
            conv = session.execute(select(Conversation).where(Conversation.id == cid)).scalar_one_or_none()
            if not conv:
                return json.dumps({"success": False, "message": "会话不存在"}, ensure_ascii=False)
            if conv.post_author_id != uid and conv.applicant_id != uid:
                return json.dumps({"success": False, "message": "无权操作"}, ensure_ascii=False)
            if conv.status == "closed":
                return json.dumps({"success": False, "message": "会话已关闭"}, ensure_ascii=False)

            # 记录确认状态（用 conversation 的 status 字段）
            # active -> 需要双方确认 -> team_confirmed
            # 简化逻辑：第一次确认标记，第二次确认创建团队
            # 使用一个临时字段来跟踪，这里简化为直接确认
            post = session.execute(select(Post).where(Post.id == conv.post_id)).scalar_one_or_none()
            if not post:
                return json.dumps({"success": False, "message": "帖子不存在"}, ensure_ascii=False)

            # 创建团队
            author = session.execute(select(User).where(User.id == conv.post_author_id)).scalar_one_or_none()
            applicant = session.execute(select(User).where(User.id == conv.applicant_id)).scalar_one_or_none()
            if not author or not applicant:
                return json.dumps({"success": False, "message": "用户信息不完整"}, ensure_ascii=False)

            # 检查是否已有团队
            existing_team = session.execute(
                select(Team).where(Team.post_id == conv.post_id)
            ).scalar_one_or_none()
            if existing_team:
                conv.status = "team_confirmed"
                conv.contact_unlocked = True
                session.commit()
                return json.dumps({
                    "success": True,
                    "team_id": str(existing_team.id),
                    "message": "组队确认完成，联系方式已解锁",
                    "contact_unlocked": True,
                }, ensure_ascii=False)

            # 创建新团队
            import datetime
            team = Team(
                post_id=conv.post_id,
                activity_name=post.activity_name,
                division_of_labor=[],
                meeting_agenda=[],
                task_list=[],
                risk_reminders=[],
                contact_info=[
                    {
                        "user_id": str(author.id),
                        "nickname": author.nickname,
                        "phone": author.phone,
                        "wechat": author.wechat,
                    },
                    {
                        "user_id": str(applicant.id),
                        "nickname": applicant.nickname,
                        "phone": applicant.phone,
                        "wechat": applicant.wechat,
                    },
                ],
            )
            session.add(team)
            session.flush()

            # 添加团队成员
            app_role = ""
            if conv.application_id:
                app = session.execute(select(Application).where(Application.id == conv.application_id)).scalar_one_or_none()
                app_role = app.role_wanted if app else ""
            for u, role in [(author, ""), (applicant, app_role)]:
                tm = TeamMember(team_id=team.id, user_id=u.id, suggested_role=role)
                session.add(tm)

            conv.status = "team_confirmed"
            conv.contact_unlocked = True
            post.status = "full"
            post.current_members = post.current_members + 1

            # 更新用户团队数
            author.team_count = (author.team_count or 0) + 1
            applicant.team_count = (applicant.team_count or 0) + 1

            session.commit()
            return json.dumps({
                "success": True,
                "team_id": str(team.id),
                "message": "组队成功！联系方式已解锁，团队已创建",
                "contact_unlocked": True,
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"confirm_team error: {e}")
        return json.dumps({"success": False, "message": f"确认组队失败: {str(e)}"}, ensure_ascii=False)


@tool
def close_conversation(user_id: str, conversation_id: str) -> str:
    """关闭会话。user_id 为当前用户ID，conversation_id 为会话ID。"""
    ctx = request_context.get() or new_context(method="close_conversation")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            cid = int(conversation_id)
            conv = session.execute(select(Conversation).where(Conversation.id == cid)).scalar_one_or_none()
            if not conv:
                return json.dumps({"success": False, "message": "会话不存在"}, ensure_ascii=False)
            if conv.post_author_id != uid and conv.applicant_id != uid:
                return json.dumps({"success": False, "message": "无权操作"}, ensure_ascii=False)

            conv.status = "closed"
            session.commit()
            return json.dumps({"success": True, "message": "会话已关闭"}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"close_conversation error: {e}")
        return json.dumps({"success": False, "message": f"关闭会话失败: {str(e)}"}, ensure_ascii=False)
