"""AI 工具：对话式发帖、分类审核、队友匹配、成队规划

使用 LLM 直接实现 AI 功能，后续裴斐提供 Coze 工作流 ID 后可切换为 Coze 调用。
"""
import os
import json
import logging
from langchain.tools import tool
from sqlalchemy import select
from coze_coding_dev_sdk import LLMClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from langchain_core.messages import SystemMessage, HumanMessage
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.post import Post
from storage.database.models.team import Team, TeamMember
from tools.auth_tools import _user_brief, _user_to_dict

logger = logging.getLogger(__name__)

MODEL_ID = "doubao-seed-2-0-pro-260215"


def _get_text_content(content) -> str:
    """安全提取 LLM 响应文本"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        return " ".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text")
    return str(content)


def _call_llm(system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
    """调用 LLM 并返回文本"""
    ctx = request_context.get() or new_context(method="ai_llm_call")
    client = LLMClient(ctx=ctx)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]
    response = client.invoke(messages=messages, model=MODEL_ID, temperature=temperature)
    return _get_text_content(response.content)


def _try_coze_workflow(workflow_env_key: str, parameters: dict) -> dict | None:
    """尝试调用 Coze 工作流，未配置则返回 None"""
    workflow_id = os.getenv(workflow_env_key, "").strip()
    if not workflow_id:
        return None
    token = os.getenv("COZE_API_TOKEN", "").strip()
    if not token:
        return None
    try:
        import requests
        base_url = os.getenv("COZE_API_BASE_URL", "https://api.coze.cn")
        resp = requests.post(
            f"{base_url}/v1/workflow/run",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"workflow_id": workflow_id, "parameters": parameters},
            timeout=60,
        )
        data = resp.json()
        if data.get("code") == 0:
            return json.loads(data.get("data", "{}")) if isinstance(data.get("data"), str) else data.get("data")
    except Exception as e:
        logger.warning(f"Coze workflow {workflow_env_key} call failed: {e}")
    return None


@tool
def ai_post_draft(message: str, draft: str = "", user_skills: str = "") -> str:
    """AI 对话式发帖助手。用户输入一句话描述组队需求，AI 追问缺失信息并生成结构化草稿。message 为用户输入，draft 为当前草稿(JSON字符串)，user_skills 为用户技能(逗号分隔)。返回追问回复和结构化草稿。"""
    ctx = request_context.get() or new_context(method="ai_post_draft")

    # 先尝试 Coze 工作流
    coze_params = {"message": message, "draft": draft, "user_skills": user_skills}
    coze_result = _try_coze_workflow("COZE_WORKFLOW_POST_DRAFT_ID", coze_params)
    if coze_result:
        return json.dumps(coze_result, ensure_ascii=False)

    # 降级: 使用 LLM 直接处理
    system_prompt = """你是 CampusMate AI 发帖助手。用户想发布组队帖，你需要：
1. 理解用户的组队需求
2. 检查信息是否完整(活动名称、目标人数、所需角色、每周时长、学校范围、截止日期、描述)
3. 如果信息不完整，礼貌追问缺失的关键信息
4. 如果信息足够，生成结构化草稿

你必须返回 JSON 格式:
{
  "reply": "给用户的回复(追问或确认)",
  "draft": {
    "activity_name": "活动名称",
    "target_members": 人数,
    "needed_roles": ["角色1", "角色2"],
    "weekly_hours": "每周时长",
    "school_scope": "学校范围",
    "deadline": "截止日期(YYYY-MM-DD)",
    "description": "详细描述"
  },
  "is_complete": true或false
}

注意:
- 如果用户信息不足，is_complete 为 false，reply 中追问缺失信息
- 如果信息足够，is_complete 为 true，draft 填充完整字段
- 不要编造用户没说的信息，缺失字段留空字符串或默认值"""

    user_msg = f"用户输入: {message}\n当前草稿: {draft}\n用户技能: {user_skills}"
    try:
        result_text = _call_llm(system_prompt, user_msg, temperature=0.5)
        # 尝试解析 JSON
        result = json.loads(result_text)
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        # 如果 LLM 没返回有效 JSON，用文本包裹
        return json.dumps({
            "reply": _get_text_content(result_text) if 'result_text' in dir() else message,
            "draft": json.loads(draft) if draft else {},
            "is_complete": False,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ai_post_draft error: {e}")
        return json.dumps({"reply": f"AI 处理出错: {str(e)}", "draft": {}, "is_complete": False}, ensure_ascii=False)


@tool
def ai_classify_review(post_title: str, post_description: str) -> str:
    """AI 分类与审核。自动对帖子进行分类、打标签、评估风险等级，并给出修改建议。post_title 为帖子标题，post_description 为帖子描述。"""
    ctx = request_context.get() or new_context(method="ai_classify_review")

    # 先尝试 Coze 工作流
    coze_params = {"title": post_title, "description": post_description}
    coze_result = _try_coze_workflow("COZE_WORKFLOW_CLASSIFY_REVIEW_ID", coze_params)
    if coze_result:
        return json.dumps(coze_result, ensure_ascii=False)

    # 降级: 使用 LLM 直接处理
    system_prompt = """你是 CampusMate AI 内容审核专家。对帖子进行分类、打标签、评估风险等级。

主分类选项(只能选一个):
- 竞赛与项目
- 学习与科研
- 体育与健身
- 旅行与户外
- 校园生活
- 拼团与AA

风险等级:
- low: 正常内容
- medium: 涉及线下见面、金钱、夜间等场景
- high: 涉及大额金钱、长途、诱导性内容等

你必须返回 JSON 格式:
{
  "main_category": "主分类",
  "tags": ["标签1", "标签2", "标签3"],
  "risk_level": "low/medium/high",
  "suggestions": ["修改建议1", "修改建议2"]
}"""

    user_msg = f"帖子标题: {post_title}\n帖子描述: {post_description}"
    try:
        result_text = _call_llm(system_prompt, user_msg, temperature=0.3)
        result = json.loads(result_text)
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({
            "main_category": "校园生活",
            "tags": [],
            "risk_level": "low",
            "suggestions": ["自动分类失败，请手动设置分类"],
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ai_classify_review error: {e}")
        return json.dumps({"error": f"AI 审核失败: {str(e)}"}, ensure_ascii=False)


@tool
def ai_match_teammates(post_id: str) -> str:
    """AI 智能匹配。根据帖子所需角色，从数据库中匹配合适的队友，输出匹配分数和推荐理由。post_id 为帖子ID。"""
    ctx = request_context.get() or new_context(method="ai_match_teammates")

    # 先尝试 Coze 工作流
    coze_params = {"post_id": post_id}
    coze_result = _try_coze_workflow("COZE_WORKFLOW_MATCH_TEAMMATES_ID", coze_params)
    if coze_result:
        return json.dumps(coze_result, ensure_ascii=False)

    # 降级: 使用 LLM + 数据库查询
    try:
        session = get_session()
        try:
            pid = int(post_id)
            post = session.execute(select(Post).where(Post.id == pid)).scalar_one_or_none()
            if not post:
                return json.dumps({"success": False, "message": "帖子不存在"}, ensure_ascii=False)

            # 查找所有认证用户(排除帖主)
            users = session.execute(
                select(User)
                .where(User.auth_status != "unverified")
                .where(User.id != post.author_id)
            ).scalars().all()

            if not users:
                return json.dumps({"success": True, "matches": [], "message": "暂无可匹配的用户"}, ensure_ascii=False)

            # 用 LLM 进行语义匹配
            needed_roles = post.needed_roles or []
            user_info = []
            for u in users[:20]:  # 限制数量避免 token 过多
                user_info.append({
                    "user_id": str(u.id),
                    "nickname": u.nickname,
                    "major": u.major,
                    "grade": u.grade,
                    "skills": u.skills or [],
                })

            system_prompt = """你是 CampusMate AI 匹配引擎。根据帖子需求，为每个候选用户生成匹配分数(0-100)和推荐理由。

匹配逻辑:
1. 技能匹配: 用户技能是否覆盖所需角色
2. 专业相关性: 专业是否与活动领域相关
3. 经验推断: 年级越高经验通常越丰富

你必须返回 JSON 格式:
{
  "matches": [
    {
      "user_id": "用户ID",
      "score": 匹配分数,
      "reason": "推荐理由(一句话)"
    }
  ]
}

按分数从高到低排序，最多返回5个。"""

            user_msg = f"""帖子信息:
- 标题: {post.title}
- 活动名称: {post.activity_name}
- 主分类: {post.main_category}
- 所需角色: {json.dumps(needed_roles, ensure_ascii=False)}
- 描述: {post.description or '无'}

候选用户:
{json.dumps(user_info, ensure_ascii=False)}"""

            result_text = _call_llm(system_prompt, user_msg, temperature=0.3)
            result = json.loads(result_text)
            return json.dumps({"success": True, "matches": result.get("matches", [])}, ensure_ascii=False)
        finally:
            session.close()
    except json.JSONDecodeError:
        return json.dumps({"success": True, "matches": [], "message": "AI 匹配分析失败"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ai_match_teammates error: {e}")
        return json.dumps({"success": False, "message": f"匹配失败: {str(e)}"}, ensure_ascii=False)


@tool
def ai_team_plan(team_id: str) -> str:
    """AI 成队规划。根据团队成员能力生成分工建议、首次会议议程、任务清单和风险提醒。team_id 为团队ID。"""
    ctx = request_context.get() or new_context(method="ai_team_plan")

    # 先尝试 Coze 工作流
    coze_params = {"team_id": team_id}
    coze_result = _try_coze_workflow("COZE_WORKFLOW_TEAM_PLAN_ID", coze_params)
    if coze_result:
        return json.dumps(coze_result, ensure_ascii=False)

    # 降级: 使用 LLM + 数据库查询
    try:
        session = get_session()
        try:
            tid = int(team_id)
            team = session.execute(select(Team).where(Team.id == tid)).scalar_one_or_none()
            if not team:
                return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)

            # 获取团队成员信息
            members = session.execute(
                select(TeamMember, User)
                .join(User, TeamMember.user_id == User.id)
                .where(TeamMember.team_id == tid)
            ).all()

            member_info = []
            for tm, user in members:
                member_info.append({
                    "user_id": str(user.id),
                    "nickname": user.nickname,
                    "major": user.major,
                    "grade": user.grade,
                    "skills": user.skills or [],
                    "suggested_role": tm.suggested_role or "",
                })

            # 获取关联帖子信息
            post = session.execute(select(Post).where(Post.id == team.post_id)).scalar_one_or_none()
            post_info = {
                "activity_name": team.activity_name,
                "needed_roles": post.needed_roles if post else [],
                "description": post.description if post else "",
            }

            system_prompt = """你是 CampusMate AI 成队规划助手。根据团队成员能力生成:
1. 分工建议: 根据每个人的技能和角色分配任务
2. 首次会议议程: 5-7个议程项(id为a1,a2...)
3. 任务清单: 3-5个具体任务(id为t1,t2...,done为false)
4. 风险提醒: 2-4条针对性风险提示

你必须返回 JSON 格式:
{
  "division_of_labor": [
    {"role": "角色名", "responsibilities": "职责描述", "member_id": "用户ID"}
  ],
  "meeting_agenda": [
    {"id": "a1", "content": "议程内容", "done": false}
  ],
  "task_list": [
    {"id": "t1", "title": "任务标题", "done": false}
  ],
  "risk_reminders": ["风险提醒1", "风险提醒2"]
}"""

            user_msg = f"""团队活动: {json.dumps(post_info, ensure_ascii=False)}
团队成员: {json.dumps(member_info, ensure_ascii=False)}"""

            result_text = _call_llm(system_prompt, user_msg, temperature=0.5)
            result = json.loads(result_text)

            # 将 AI 生成结果更新到数据库
            team.division_of_labor = result.get("division_of_labor", [])
            team.meeting_agenda = result.get("meeting_agenda", [])
            team.task_list = result.get("task_list", [])
            team.risk_reminders = result.get("risk_reminders", [])
            session.commit()

            return json.dumps({"success": True, "team_plan": result, "message": "AI 成队规划已生成并保存"}, ensure_ascii=False)
        finally:
            session.close()
    except json.JSONDecodeError:
        return json.dumps({"success": False, "message": "AI 规划生成失败，请重试"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ai_team_plan error: {e}")
        return json.dumps({"success": False, "message": f"成队规划失败: {str(e)}"}, ensure_ascii=False)
