"""消息工具：会话列表、聊天消息、发送消息、确认组队、关闭会话"""
import json
import logging
import datetime
from dataclasses import asdict
from langchain.tools import tool
from sqlalchemy import select, desc, or_, func
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.post import Post
from storage.database.models.conversation import Conversation, Message
from storage.database.models.application import Application
from storage.database.models.team import Team, TeamMember
from services.content_moderation import ModerationContext, moderate_content
from services.abuse_monitoring import check_and_record
from services.moderation_cases import (
    create_case_from_event,
    has_active_restriction,
    record_moderation_event,
    users_are_blocked,
)
from services.notifications import notify
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
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
        "is_mine": is_mine,
    }


@tool
def get_conversations(user_id: str, page: int = 1, page_size: int = 20) -> str:
    """获取会话列表。user_id 为当前用户ID。"""
    ctx = request_context.get() or new_context(method="get_conversations")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            page = max(1, int(page))
            page_size = min(100, max(1, int(page_size)))
            filters = or_(Conversation.post_author_id == uid, Conversation.applicant_id == uid)
            total = session.scalar(select(func.count()).select_from(Conversation).where(filters)) or 0
            results = session.execute(
                select(Conversation)
                .where(filters)
                .order_by(desc(Conversation.last_message_at), desc(Conversation.id))
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars().all()

            convs = []
            for conv in results:
                other_id = conv.applicant_id if conv.post_author_id == uid else conv.post_author_id
                other_user = session.execute(select(User).where(User.id == other_id)).scalar_one_or_none()
                post = session.execute(select(Post).where(Post.id == conv.post_id)).scalar_one_or_none()
                item = _conversation_to_dict(conv, other_user, post)
                item["unread_count"] = int(
                    session.scalar(
                        select(func.count()).select_from(Message).where(
                            Message.conversation_id == conv.id,
                            Message.sender_id != uid,
                            Message.read_at.is_(None),
                        )
                    )
                    or 0
                )
                convs.append(item)

            return json.dumps(
                {
                    "success": True,
                    "list": convs,
                    "total": int(total),
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": int(total),
                        "pages": (int(total) + page_size - 1) // page_size,
                    },
                },
                ensure_ascii=False,
            )
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_conversations error: {e}")
        return json.dumps({"success": False, "message": f"获取会话失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_messages(user_id: str, conversation_id: str, page: int = 1, page_size: int = 50) -> str:
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

            page = max(1, int(page))
            page_size = min(100, max(1, int(page_size)))
            total = session.scalar(
                select(func.count()).select_from(Message).where(Message.conversation_id == cid)
            ) or 0
            now = datetime.datetime.now(datetime.timezone.utc)
            unread = session.execute(
                select(Message).where(
                    Message.conversation_id == cid,
                    Message.sender_id != uid,
                    Message.read_at.is_(None),
                )
            ).scalars().all()
            for message in unread:
                message.read_at = now
            results = session.execute(
                select(Message)
                .where(Message.conversation_id == cid)
                .order_by(Message.created_at, Message.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars().all()
            session.commit()

            messages = [_message_to_dict(m, m.sender_id == uid) for m in results]
            return json.dumps(
                {
                    "success": True,
                    "list": messages,
                    "total": int(total),
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": int(total),
                        "pages": (int(total) + page_size - 1) // page_size,
                    },
                },
                ensure_ascii=False,
            )
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
            if has_active_restriction(session, uid, "messaging"):
                return json.dumps(
                    {"success": False, "message": "当前账号处于私信限制期，暂时不能发送消息"},
                    ensure_ascii=False,
                )
            other_user_id = conv.applicant_id if conv.post_author_id == uid else conv.post_author_id
            if users_are_blocked(session, uid, other_user_id):
                return json.dumps(
                    {"success": False, "message": "你与对方之间存在屏蔽关系，无法发送消息"},
                    ensure_ascii=False,
                )

            abuse = check_and_record(
                session,
                user_id=uid,
                event_type="message",
                target_id=f"conversation:{cid}",
                content=content,
            )
            if abuse.action in {"cooldown", "review"}:
                session.commit()
                return json.dumps(
                    {
                        "success": False,
                        "message": "消息发送过于频繁，请稍后再试",
                        "retry_after_seconds": abuse.retry_after_seconds,
                    },
                    ensure_ascii=False,
                )

            moderation = moderate_content(
                content,
                ModerationContext(
                    surface="message",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    contact_unlocked=bool(conv.contact_unlocked),
                ),
            )
            if moderation.action != "allow":
                bypass = None
                if any(rule_id.startswith("contact.") for rule_id in moderation.rule_ids):
                    bypass = check_and_record(
                        session,
                        user_id=uid,
                        event_type="contact_bypass",
                        target_id=f"conversation:{cid}",
                        content=content,
                    )
                event = record_moderation_event(
                    session,
                    actor_id=uid,
                    surface="message",
                    target_type="user",
                    target_id=str(uid),
                    action=moderation.action,
                    risk_level=moderation.risk_level,
                    rule_ids=moderation.rule_ids,
                    raw_excerpt=content,
                    source="rules",
                )
                if moderation.action in {"review", "block"} or (
                    bypass is not None and bypass.action == "review"
                ):
                    create_case_from_event(
                        session,
                        event,
                        subject_user_id=uid,
                        reason_code=moderation.rule_ids[0] if moderation.rule_ids else "content_risk",
                        priority="high" if moderation.action == "block" else "normal",
                    )
                session.commit()
                logger.info(
                    "Message moderation rejected user=%s conversation=%s action=%s rules=%s",
                    user_id,
                    conversation_id,
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
            sender = session.get(User, uid)
            notify(
                session,
                user_id=other_user_id,
                event_type="message.created",
                title="收到新消息",
                body=f"{sender.nickname if sender else '有同学'} 给你发来一条消息",
                target_type="conversation",
                target_id=str(conv.id),
                dedupe_key=f"message:{msg.id}:created",
            )

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

            if uid == conv.post_author_id:
                conv.author_confirmed = True
            else:
                conv.applicant_confirmed = True

            if not (conv.author_confirmed and conv.applicant_confirmed):
                other_user_id = (
                    conv.applicant_id if uid == conv.post_author_id else conv.post_author_id
                )
                notify(
                    session,
                    user_id=other_user_id,
                    event_type="team.confirmation.requested",
                    title="等待确认组队",
                    body="对方已确认组队，请查看并完成确认",
                    target_type="conversation",
                    target_id=str(conv.id),
                    dedupe_key=f"conversation:{conv.id}:confirmation:{uid}",
                )
                session.commit()
                return json.dumps(
                    {
                        "success": True,
                        "message": "已确认组队，等待对方确认",
                        "contact_unlocked": False,
                        "waiting_for_other": True,
                    },
                    ensure_ascii=False,
                )

            post = session.execute(select(Post).where(Post.id == conv.post_id)).scalar_one_or_none()
            if not post:
                return json.dumps({"success": False, "message": "帖子不存在"}, ensure_ascii=False)

            # 创建团队
            author = session.execute(select(User).where(User.id == conv.post_author_id)).scalar_one_or_none()
            applicant = session.execute(select(User).where(User.id == conv.applicant_id)).scalar_one_or_none()
            if not author or not applicant:
                return json.dumps({"success": False, "message": "用户信息不完整"}, ensure_ascii=False)

            # 同一帖子只建立一个团队，后续双方确认的申请者加入已有团队。
            existing_team = session.execute(
                select(Team).where(Team.post_id == conv.post_id)
            ).scalar_one_or_none()
            if existing_team:
                if existing_team.owner_id is None:
                    existing_team.owner_id = author.id
                member_ids = set(
                    session.execute(
                        select(TeamMember.user_id).where(
                            TeamMember.team_id == existing_team.id
                        )
                    ).scalars()
                )
                contact_info = list(existing_team.contact_info or [])
                contact_ids = {str(item.get("user_id")) for item in contact_info}
                for participant in (author, applicant):
                    if participant.id not in member_ids:
                        session.add(
                            TeamMember(
                                team_id=existing_team.id,
                                user_id=participant.id,
                                suggested_role="",
                                member_role="owner" if participant.id == existing_team.owner_id else "member",
                            )
                        )
                        member_ids.add(participant.id)
                        participant.team_count = (participant.team_count or 0) + 1
                    if str(participant.id) not in contact_ids:
                        contact_info.append(
                            {
                                "user_id": str(participant.id),
                                "nickname": participant.nickname,
                                "phone": participant.phone,
                                "wechat": participant.wechat,
                            }
                        )
                        contact_ids.add(str(participant.id))
                existing_team.contact_info = contact_info
                conv.status = "team_confirmed"
                conv.contact_unlocked = True
                post.current_members = len(member_ids)
                post.status = (
                    "full" if post.current_members >= post.target_members else "recruiting"
                )
                for participant_id in (author.id, applicant.id):
                    notify(
                        session,
                        user_id=participant_id,
                        event_type="team.confirmed",
                        title="组队已确认",
                        body=f"「{post.title}」组队已完成，联系方式已解锁",
                        target_type="team",
                        target_id=str(existing_team.id),
                        dedupe_key=f"conversation:{conv.id}:team:{existing_team.id}:user:{participant_id}",
                    )
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
                owner_id=author.id,
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
                tm = TeamMember(
                    team_id=team.id,
                    user_id=u.id,
                    suggested_role=role,
                    member_role="owner" if u.id == author.id else "member",
                )
                session.add(tm)

            conv.status = "team_confirmed"
            conv.contact_unlocked = True
            post.current_members = 2
            post.status = "full" if post.current_members >= post.target_members else "recruiting"

            # 更新用户团队数
            author.team_count = (author.team_count or 0) + 1
            applicant.team_count = (applicant.team_count or 0) + 1

            for participant_id in (author.id, applicant.id):
                notify(
                    session,
                    user_id=participant_id,
                    event_type="team.confirmed",
                    title="组队已确认",
                    body=f"「{post.title}」组队已完成，联系方式已解锁",
                    target_type="team",
                    target_id=str(team.id),
                    dedupe_key=f"conversation:{conv.id}:team:{team.id}:user:{participant_id}",
                )

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
