"""团队工具：团队详情、更新任务、我的团队"""
import json
import logging
from langchain.tools import tool
from sqlalchemy import select, desc
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.team import Team, TeamMember
from tools.auth_tools import _user_brief

logger = logging.getLogger(__name__)


def _team_to_dict(team: Team, members: list | None = None) -> dict:
    data = {
        "id": str(team.id),
        "post_id": str(team.post_id),
        "activity_name": team.activity_name,
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
            task_list = team.task_list or []
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
def get_my_teams(user_id: str) -> str:
    """获取我参与的团队。user_id 为当前用户ID。"""
    ctx = request_context.get() or new_context(method="get_my_teams")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            member_records = session.execute(
                select(TeamMember, Team)
                .join(Team, TeamMember.team_id == Team.id)
                .where(TeamMember.user_id == uid)
                .order_by(desc(Team.created_at))
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

            return json.dumps({"success": True, "list": teams, "total": len(teams)}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_my_teams error: {e}")
        return json.dumps({"success": False, "message": f"获取团队失败: {str(e)}"}, ensure_ascii=False)
