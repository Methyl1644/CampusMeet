"""团队工具：团队详情、更新任务、我的团队"""
import json
import logging
import uuid
from langchain.tools import tool
from sqlalchemy import select, desc, func
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.team import (
    TEAM_TASK_CAPACITY_MESSAGE,
    TEAM_TASK_LIMIT,
    Team,
    TeamMember,
    normalize_team_task_list,
)
from storage.database.models.post import Post
from storage.database.models.content import AuditLog
from services.collaboration_lifecycle import deadline_has_passed
from tools.auth_tools import _user_brief

logger = logging.getLogger(__name__)


def _team_to_dict(team: Team, members: list | None = None) -> dict:
    data = {
        "id": str(team.id),
        "post_id": str(team.post_id),
        "owner_id": str(team.owner_id) if team.owner_id is not None else None,
        "activity_name": team.activity_name,
        "status": team.status,
        "division_of_labor": team.division_of_labor or [],
        "meeting_agenda": team.meeting_agenda or [],
        "task_list": team.task_list or [],
        "risk_reminders": team.risk_reminders or [],
        "contact_info": team.contact_info or [],
        "created_at": team.created_at.isoformat() if team.created_at else None,
    }
    if members:
        data["members"] = members
    return data


@tool
def get_team_detail(user_id: str, team_id: str) -> str:
    """获取团队详情。user_id 为当前用户ID，team_id 为团队ID。只有团队成员可查看联系方式。"""
    ctx = request_context.get() or new_context(method="get_team_detail")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            tid = int(team_id)
            team = session.execute(select(Team).where(Team.id == tid)).scalar_one_or_none()
            if not team:
                return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)

            # 检查是否为团队成员
            member_records = session.execute(
                select(TeamMember).where(TeamMember.team_id == tid)
            ).scalars().all()
            is_member = any(m.user_id == uid for m in member_records)
            if not is_member:
                return json.dumps({"success": False, "message": "无权查看此团队"}, ensure_ascii=False)

            # 获取成员详细信息
            members = []
            for m in member_records:
                user = session.execute(select(User).where(User.id == m.user_id)).scalar_one_or_none()
                if user:
                    members.append({
                        "user": _user_brief(user),
                        "suggested_role": m.suggested_role,
                        "member_role": m.member_role,
                    })

            team_data = _team_to_dict(team, members)
            # 非成员不返回联系方式
            if not is_member:
                team_data["contact_info"] = []

            return json.dumps({"success": True, "team": team_data}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_team_detail error: {e}")
        return json.dumps({"success": False, "message": f"获取团队详情失败: {str(e)}"}, ensure_ascii=False)


@tool
def update_team_task(user_id: str, team_id: str, task_id: str, done: bool) -> str:
    """更新团队任务状态。user_id 为当前用户ID，team_id 为团队ID，task_id 为任务ID(在task_list中的id)，done 为是否完成。"""
    ctx = request_context.get() or new_context(method="update_team_task")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            tid = int(team_id)
            team = session.execute(select(Team).where(Team.id == tid)).scalar_one_or_none()
            if not team:
                return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)

            # 检查是否为团队成员
            member = session.execute(
                select(TeamMember)
                .where(TeamMember.team_id == tid)
                .where(TeamMember.user_id == uid)
            ).scalar_one_or_none()
            if not member:
                return json.dumps({"success": False, "message": "无权操作此团队"}, ensure_ascii=False)

            # 更新任务状态
            task_list = [dict(item) for item in (team.task_list or []) if isinstance(item, dict)]
            updated = False
            for task in task_list:
                if isinstance(task, dict) and task.get("id") == task_id:
                    task["done"] = done
                    updated = True
                    break

            if not updated:
                return json.dumps({"success": False, "message": "任务不存在"}, ensure_ascii=False)

            team.task_list = task_list
            session.commit()

            return json.dumps({
                "success": True,
                "message": f"任务已{'标记为完成' if done else '标记为未完成'}",
                "team": _team_to_dict(team),
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"update_team_task error: {e}")
        return json.dumps({"success": False, "message": f"更新任务失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_my_teams(user_id: str, page: int = 1, page_size: int = 20) -> str:
    """获取我参与的团队。user_id 为当前用户ID。"""
    ctx = request_context.get() or new_context(method="get_my_teams")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            page = max(1, int(page))
            page_size = min(100, max(1, int(page_size)))
            total = int(
                session.scalar(
                    select(func.count()).select_from(TeamMember).where(TeamMember.user_id == uid)
                )
                or 0
            )
            member_records = session.execute(
                select(TeamMember, Team)
                .join(Team, TeamMember.team_id == Team.id)
                .where(TeamMember.user_id == uid)
                .order_by(desc(Team.created_at), desc(Team.id))
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()

            teams = []
            for member, team in member_records:
                teams.append({
                    "id": str(team.id),
                    "post_id": str(team.post_id),
                    "activity_name": team.activity_name,
                    "my_role": member.suggested_role,
                    "created_at": team.created_at.isoformat() if team.created_at else None,
                })

            return json.dumps(
                {
                    "success": True,
                    "list": teams,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
                ensure_ascii=False,
            )
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_my_teams error: {e}")
        return json.dumps({"success": False, "message": f"获取团队失败: {str(e)}"}, ensure_ascii=False)


def _member(session, team_id: int, user_id: int) -> TeamMember | None:
    return session.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    ).scalar_one_or_none()


def _owner_id(session, team: Team) -> int | None:
    if team.owner_id is not None:
        return team.owner_id
    post = session.get(Post, team.post_id)
    if post is not None:
        team.owner_id = post.author_id
        owner = _member(session, team.id, post.author_id)
        if owner is not None:
            owner.member_role = "owner"
        return post.author_id
    return None


def _team_audit(session, actor_id: int, action: str, team: Team, detail: dict) -> None:
    session.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            target_type="team",
            target_id=str(team.id),
            detail=json.dumps(detail, ensure_ascii=False),
        )
    )


@tool
def create_team_task(
    user_id: str,
    team_id: str,
    title: str,
    assignee_id: str = "",
    due_at: str = "",
) -> str:
    """创建团队任务。"""
    session = get_session()
    try:
        uid, tid = int(user_id), int(team_id)
        team = session.get(Team, tid)
        if not team:
            return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)
        if team.status != "active":
            return json.dumps({"success": False, "message": "团队已归档，不能再创建任务"}, ensure_ascii=False)
        if not _member(session, tid, uid):
            return json.dumps({"success": False, "message": "无权操作此团队"}, ensure_ascii=False)
        if len(team.task_list or []) >= TEAM_TASK_LIMIT:
            return json.dumps(
                {"success": False, "message": f"任务数量已达上限（{TEAM_TASK_LIMIT} 个）"},
                ensure_ascii=False,
            )
        normalized_title = title.strip()[:120]
        if not normalized_title:
            return json.dumps({"success": False, "message": "请填写任务名称"}, ensure_ascii=False)
        resolved_assignee = int(assignee_id) if assignee_id else None
        if resolved_assignee is not None and not _member(session, tid, resolved_assignee):
            return json.dumps({"success": False, "message": "任务负责人不是团队成员"}, ensure_ascii=False)
        task = {
            "id": uuid.uuid4().hex,
            "title": normalized_title,
            "assignee_id": str(resolved_assignee) if resolved_assignee is not None else None,
            "due_at": due_at.strip()[:40] or None,
            "done": False,
        }
        bounded_tasks = normalize_team_task_list([*(team.task_list or []), task])
        persisted_task = next(
            (item for item in bounded_tasks if item.get("id") == task["id"]),
            None,
        )
        if persisted_task is None:
            return json.dumps(
                {"success": False, "message": TEAM_TASK_CAPACITY_MESSAGE},
                ensure_ascii=False,
            )
        team.task_list = bounded_tasks
        _team_audit(session, uid, "team.task_create", team, {"task_id": task["id"]})
        session.commit()
        session.refresh(team)
        persisted_task = next(
            (item for item in (team.task_list or []) if item.get("id") == task["id"]),
            None,
        )
        if persisted_task is None:
            return json.dumps(
                {"success": False, "message": TEAM_TASK_CAPACITY_MESSAGE},
                ensure_ascii=False,
            )
        return json.dumps(
            {"success": True, "task": persisted_task, "team": _team_to_dict(team)},
            ensure_ascii=False,
        )
    finally:
        session.close()


@tool
def delete_team_task(user_id: str, team_id: str, task_id: str) -> str:
    """删除团队任务。"""
    session = get_session()
    try:
        uid, tid = int(user_id), int(team_id)
        team = session.get(Team, tid)
        if not team:
            return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)
        if _owner_id(session, team) != uid:
            return json.dumps({"success": False, "message": "仅队长可以删除团队任务"}, ensure_ascii=False)
        tasks = [dict(item) for item in (team.task_list or []) if isinstance(item, dict)]
        remaining = [item for item in tasks if str(item.get("id")) != task_id]
        if len(remaining) == len(tasks):
            return json.dumps({"success": False, "message": "任务不存在"}, ensure_ascii=False)
        team.task_list = remaining
        _team_audit(session, uid, "team.task_delete", team, {"task_id": task_id})
        session.commit()
        return json.dumps({"success": True, "team": _team_to_dict(team)}, ensure_ascii=False)
    finally:
        session.close()


@tool
def transfer_team_owner(user_id: str, team_id: str, target_user_id: str) -> str:
    """转让团队队长。"""
    session = get_session()
    try:
        uid, tid, target_id = int(user_id), int(team_id), int(target_user_id)
        team = session.get(Team, tid)
        if not team:
            return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)
        if _owner_id(session, team) != uid:
            return json.dumps({"success": False, "message": "仅队长可以转让团队"}, ensure_ascii=False)
        target = _member(session, tid, target_id)
        current = _member(session, tid, uid)
        if not target:
            return json.dumps({"success": False, "message": "目标用户不是团队成员"}, ensure_ascii=False)
        team.owner_id = target_id
        target.member_role = "owner"
        if current:
            current.member_role = "member"
        _team_audit(session, uid, "team.owner_transfer", team, {"target_user_id": target_id})
        session.commit()
        return json.dumps({"success": True, "owner_id": str(target_id), "team": _team_to_dict(team)}, ensure_ascii=False)
    finally:
        session.close()


def _remove_member_record(session, team: Team, member: TeamMember, actor_id: int) -> None:
    target_id = member.user_id
    session.delete(member)
    user = session.get(User, target_id)
    if user:
        user.team_count = max(0, (user.team_count or 0) - 1)
    team.contact_info = [
        item for item in (team.contact_info or []) if str(item.get("user_id")) != str(target_id)
    ]
    session.flush()
    remaining = int(
        session.scalar(select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team.id))
        or 0
    )
    post = session.get(Post, team.post_id)
    if post:
        post.current_members = remaining
        if remaining < post.target_members and post.status == "full":
            post.status = "closed" if deadline_has_passed(post) else "recruiting"
    _team_audit(session, actor_id, "team.member_remove", team, {"target_user_id": target_id})


@tool
def leave_team(user_id: str, team_id: str) -> str:
    """离开团队。"""
    session = get_session()
    try:
        uid, tid = int(user_id), int(team_id)
        team = session.get(Team, tid)
        member = _member(session, tid, uid) if team else None
        if not team or not member:
            return json.dumps({"success": False, "message": "你不是该团队成员"}, ensure_ascii=False)
        if _owner_id(session, team) == uid:
            return json.dumps({"success": False, "message": "队长需先转让团队后才能离开"}, ensure_ascii=False)
        _remove_member_record(session, team, member, uid)
        session.commit()
        return json.dumps({"success": True, "message": "已离开团队"}, ensure_ascii=False)
    finally:
        session.close()


@tool
def remove_team_member(user_id: str, team_id: str, target_user_id: str) -> str:
    """队长移除团队成员。"""
    session = get_session()
    try:
        uid, tid, target_id = int(user_id), int(team_id), int(target_user_id)
        team = session.get(Team, tid)
        if not team:
            return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)
        if _owner_id(session, team) != uid:
            return json.dumps({"success": False, "message": "仅队长可以移除成员"}, ensure_ascii=False)
        if target_id == uid:
            return json.dumps({"success": False, "message": "队长不能移除自己"}, ensure_ascii=False)
        member = _member(session, tid, target_id)
        if not member:
            return json.dumps({"success": False, "message": "团队成员不存在"}, ensure_ascii=False)
        _remove_member_record(session, team, member, uid)
        session.commit()
        return json.dumps({"success": True, "message": "成员已移除"}, ensure_ascii=False)
    finally:
        session.close()


@tool
def edit_team_task(
    user_id: str,
    team_id: str,
    task_id: str,
    title: str,
    assignee_id: str = "",
    due_at: str = "",
) -> str:
    """编辑团队任务。"""
    session = get_session()
    try:
        uid, tid = int(user_id), int(team_id)
        team = session.get(Team, tid)
        if not team or not _member(session, tid, uid):
            return json.dumps({"success": False, "message": "无权操作此团队"}, ensure_ascii=False)
        if team.status != "active":
            return json.dumps({"success": False, "message": "团队已归档"}, ensure_ascii=False)
        resolved_assignee = int(assignee_id) if assignee_id else None
        if resolved_assignee is not None and not _member(session, tid, resolved_assignee):
            return json.dumps({"success": False, "message": "任务负责人不是团队成员"}, ensure_ascii=False)
        normalized_title = title.strip()[:120]
        if not normalized_title:
            return json.dumps({"success": False, "message": "请填写任务名称"}, ensure_ascii=False)
        tasks = [dict(item) for item in (team.task_list or []) if isinstance(item, dict)]
        task = next((item for item in tasks if str(item.get("id")) == task_id), None)
        if task is None:
            return json.dumps({"success": False, "message": "任务不存在"}, ensure_ascii=False)
        task.update(
            {
                "title": normalized_title,
                "assignee_id": str(resolved_assignee) if resolved_assignee is not None else None,
                "due_at": due_at.strip()[:40] or None,
            }
        )
        team.task_list = tasks
        _team_audit(session, uid, "team.task_edit", team, {"task_id": task_id})
        session.commit()
        return json.dumps({"success": True, "task": task, "team": _team_to_dict(team)}, ensure_ascii=False)
    finally:
        session.close()


@tool
def reorder_team_tasks(user_id: str, team_id: str, task_ids: str) -> str:
    """重排团队任务。"""
    session = get_session()
    try:
        uid, tid = int(user_id), int(team_id)
        team = session.get(Team, tid)
        if not team or not _member(session, tid, uid):
            return json.dumps({"success": False, "message": "无权操作此团队"}, ensure_ascii=False)
        requested = [item.strip() for item in task_ids.split(",") if item.strip()]
        tasks = [dict(item) for item in (team.task_list or []) if isinstance(item, dict)]
        task_map = {str(item.get("id")): item for item in tasks}
        if len(requested) != len(tasks) or set(requested) != set(task_map):
            return json.dumps({"success": False, "message": "任务排序列表不完整"}, ensure_ascii=False)
        team.task_list = [task_map[item] for item in requested]
        _team_audit(session, uid, "team.task_reorder", team, {"task_ids": requested})
        session.commit()
        return json.dumps({"success": True, "team": _team_to_dict(team)}, ensure_ascii=False)
    finally:
        session.close()


@tool
def update_team_member_role(
    user_id: str,
    team_id: str,
    target_user_id: str,
    suggested_role: str,
) -> str:
    """更新团队成员职责。"""
    session = get_session()
    try:
        uid, tid, target_id = int(user_id), int(team_id), int(target_user_id)
        team = session.get(Team, tid)
        if not team:
            return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)
        if _owner_id(session, team) != uid:
            return json.dumps({"success": False, "message": "仅队长可以调整成员职责"}, ensure_ascii=False)
        member = _member(session, tid, target_id)
        if not member:
            return json.dumps({"success": False, "message": "团队成员不存在"}, ensure_ascii=False)
        member.suggested_role = suggested_role.strip()[:80] or None
        _team_audit(
            session,
            uid,
            "team.member_role_update",
            team,
            {"target_user_id": target_id, "suggested_role": member.suggested_role},
        )
        session.commit()
        return json.dumps({"success": True, "suggested_role": member.suggested_role}, ensure_ascii=False)
    finally:
        session.close()


@tool
def archive_team(user_id: str, team_id: str) -> str:
    """归档团队。"""
    session = get_session()
    try:
        uid, tid = int(user_id), int(team_id)
        team = session.get(Team, tid)
        if not team:
            return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)
        if _owner_id(session, team) != uid:
            return json.dumps({"success": False, "message": "仅队长可以归档团队"}, ensure_ascii=False)
        team.status = "archived"
        _team_audit(session, uid, "team.archive", team, {"status": "archived"})
        session.commit()
        return json.dumps({"success": True, "team": _team_to_dict(team)}, ensure_ascii=False)
    finally:
        session.close()
