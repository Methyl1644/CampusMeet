"""FastAPI REST 路由层：把前端 /api/* 请求对接到已写好的 tool 函数。

设计：
- 每个 tool 在 tools/*.py 里已用 @tool 装饰，通过 tool.invoke(kwargs) 调用
- 需要登录的接口从 Authorization 头解析 JWT 拿 user_id，注入 tool 参数
- tool 返回 JSON 字符串，本层 json.loads 后包装成 {code, message, data}
- 字段转换规则见 docs/api-alignment.md

挂载：src/main.py 里 app.include_router(api_router, prefix="/api")
"""
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from utils.auth import verify_token
from tools.auth_tools import (
    register_auth_send_code,
    register_user,
    login_user,
    verify_campus_email,
    get_user_profile,
    update_user_profile,
)
from tools.post_tools import create_post, list_posts, get_post_detail, get_my_posts
from tools.application_tools import (
    create_application,
    get_applications,
    accept_application,
    reject_application,
    get_my_applications,
)
from tools.message_tools import (
    get_conversations,
    get_messages,
    send_message,
    confirm_team,
    close_conversation,
)
from tools.team_tools import get_team_detail, update_team_task, get_my_teams
from tools.ai_tools import (
    ai_post_draft,
    ai_classify_review,
    ai_match_teammates,
    ai_team_plan,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 工具函数 ====================

def _require_user_id(authorization: Optional[str]) -> str:
    """从 Authorization 头解析 user_id。未登录或 token 无效抛 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    return str(payload["user_id"])


def _ok(data: Any, message: str = "ok") -> dict:
    """统一成功响应 {code:0, message, data}"""
    return {"code": 0, "message": message, "data": data}


def _call(tool_func, **kwargs) -> Any:
    """调用 tool，解析返回的 JSON 字符串。

    用 .invoke() 走 langchain 官方 API（兼容各版本），参数 dict 的 key 匹配
    tool 签名即可。tool 返回 str(JSON)，这里 json.loads 还原成 dict。

    tool 业务失败时返回 {success:False, message:...}，这里透传给前端，
    前端按 data.success 判断。HTTP 层不报错（除非是参数/鉴权问题）。
    """
    try:
        raw = tool_func.invoke(kwargs)
    except Exception as e:
        logger.exception(f"tool {tool_func.name} invoke failed")
        return {"success": False, "message": f"后端调用失败: {e}"}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"success": False, "message": "后端返回格式错误", "raw": raw}


# ==================== 1. 认证模块 ====================

class SendCodeReq(BaseModel):
    account: str


class RegisterReq(BaseModel):
    account: str
    code: str
    password: str
    nickname: str
    major: str
    grade: str
    skills: list[str] = []
    wechat: str = ""


class LoginReq(BaseModel):
    account: str
    password: str


class VerifyEmailReq(BaseModel):
    email: str
    code: str


class UpdateProfileReq(BaseModel):
    nickname: str = ""
    major: str = ""
    grade: str = ""
    skills: list[str] = []
    wechat: str = ""


@router.post("/auth/send-code")
async def api_send_code(req: SendCodeReq):
    result = _call(register_auth_send_code, account=req.account)
    return _ok(result)


@router.post("/auth/register")
async def api_register(req: RegisterReq):
    result = _call(
        register_user,
        account=req.account,
        code=req.code,
        password=req.password,
        nickname=req.nickname,
        major=req.major,
        grade=req.grade,
        skills=",".join(req.skills),
        wechat=req.wechat,
    )
    return _ok(result)


@router.post("/auth/login")
async def api_login(req: LoginReq):
    result = _call(login_user, account=req.account, password=req.password)
    return _ok(result)


@router.post("/auth/verify-email")
async def api_verify_email(req: VerifyEmailReq, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(verify_campus_email, user_id=user_id, email=req.email, code=req.code)
    return _ok(result)


@router.get("/auth/profile")
async def api_get_profile(authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(get_user_profile, user_id=user_id)
    return _ok(result)


@router.patch("/auth/profile")
async def api_update_profile(req: UpdateProfileReq, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(
        update_user_profile,
        user_id=user_id,
        nickname=req.nickname,
        major=req.major,
        grade=req.grade,
        skills=",".join(req.skills),
        wechat=req.wechat,
    )
    return _ok(result)


# ==================== 2. 帖子模块 ====================

class CreatePostReq(BaseModel):
    title: str
    description: str = ""
    main_category: str
    activity_name: str
    target_members: int
    needed_roles: list[str] = []
    weekly_hours: str = ""
    school_scope: str = ""
    deadline: str = ""


@router.get("/posts")
async def api_list_posts(
    tab: str = "recommend",
    page: int = 1,
    page_size: int = 10,
    category: str = "",
    tags: str = "",
    keyword: str = "",
    sort: str = "latest",
):
    result = _call(
        list_posts,
        tab=tab, page=page, page_size=page_size,
        category=category, tags=tags, keyword=keyword, sort=sort,
    )
    return _ok(result)


@router.get("/posts/{post_id}")
async def api_get_post_detail(post_id: str):
    result = _call(get_post_detail, post_id=post_id)
    return _ok(result)


@router.post("/posts")
async def api_create_post(req: CreatePostReq, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(
        create_post,
        user_id=user_id,
        title=req.title,
        description=req.description,
        main_category=req.main_category,
        activity_name=req.activity_name,
        target_members=req.target_members,
        needed_roles=",".join(req.needed_roles),
        weekly_hours=req.weekly_hours,
        school_scope=req.school_scope,
        deadline=req.deadline,
    )
    return _ok(result)


@router.get("/posts/my")
async def api_get_my_posts(authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(get_my_posts, user_id=user_id)
    return _ok(result)


# ==================== 3. AI 智能模块 ====================

class PostDraftReq(BaseModel):
    message: str
    draft: Optional[dict] = None
    user_skills: Optional[list[str]] = None


class ClassifyReviewReq(BaseModel):
    title: str = ""
    description: str = ""
    # 兼容前端可能直接传 Partial<Post> 的其他字段，这里只取需要的


class MatchReq(BaseModel):
    post_id: str


class TeamPlanReq(BaseModel):
    team_id: str


@router.post("/agent/post-draft")
async def api_post_draft(req: PostDraftReq):
    result = _call(
        ai_post_draft,
        message=req.message,
        draft=json.dumps(req.draft, ensure_ascii=False) if req.draft else "",
        user_skills=",".join(req.user_skills) if req.user_skills else "",
    )
    return _ok(result)


@router.post("/agent/classify-review")
async def api_classify_review(req: ClassifyReviewReq):
    result = _call(
        ai_classify_review,
        post_title=req.title,
        post_description=req.description,
    )
    return _ok(result)


@router.post("/agent/match")
async def api_match(req: MatchReq):
    result = _call(ai_match_teammates, post_id=req.post_id)
    return _ok(result)


@router.post("/agent/team-plan")
async def api_team_plan(req: TeamPlanReq):
    result = _call(ai_team_plan, team_id=req.team_id)
    return _ok(result)


# ==================== 4. 申请模块 ====================

class CreateApplicationReq(BaseModel):
    post_id: str
    role_wanted: str
    experience: str
    available_time: str
    reason: str
    questions: list[str] = []


@router.post("/applications")
async def api_create_application(req: CreateApplicationReq, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(
        create_application,
        user_id=user_id,
        post_id=req.post_id,
        role_wanted=req.role_wanted,
        experience=req.experience,
        available_time=req.available_time,
        reason=req.reason,
        questions=",".join(req.questions),
    )
    return _ok(result)


@router.get("/applications")
async def api_get_applications(
    authorization: Optional[str] = Header(None),
    post_id: str = "",
):
    user_id = _require_user_id(authorization)
    result = _call(get_applications, user_id=user_id, post_id=post_id)
    return _ok(result)


@router.post("/applications/{application_id}/accept")
async def api_accept_application(application_id: str, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(accept_application, user_id=user_id, application_id=application_id)
    return _ok(result)


@router.post("/applications/{application_id}/reject")
async def api_reject_application(application_id: str, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(reject_application, user_id=user_id, application_id=application_id)
    return _ok(result)


@router.get("/applications/my")
async def api_get_my_applications(authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(get_my_applications, user_id=user_id)
    return _ok(result)


# ==================== 5. 消息模块 ====================

class SendMessageReq(BaseModel):
    content: str


@router.get("/messages/conversations")
async def api_get_conversations(authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(get_conversations, user_id=user_id)
    return _ok(result)


@router.get("/messages/{conversation_id}")
async def api_get_messages(conversation_id: str, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(get_messages, user_id=user_id, conversation_id=conversation_id)
    return _ok(result)


@router.post("/messages/{conversation_id}/send")
async def api_send_message(conversation_id: str, req: SendMessageReq, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(
        send_message,
        user_id=user_id, conversation_id=conversation_id, content=req.content,
    )
    return _ok(result)


@router.post("/messages/{conversation_id}/confirm-team")
async def api_confirm_team(conversation_id: str, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(confirm_team, user_id=user_id, conversation_id=conversation_id)
    return _ok(result)


@router.post("/messages/{conversation_id}/close")
async def api_close_conversation(conversation_id: str, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(close_conversation, user_id=user_id, conversation_id=conversation_id)
    return _ok(result)


# ==================== 6. 团队模块 ====================

class UpdateTaskReq(BaseModel):
    done: bool


@router.get("/teams/{team_id}")
async def api_get_team_detail(team_id: str, authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(get_team_detail, user_id=user_id, team_id=team_id)
    return _ok(result)


@router.patch("/teams/{team_id}/tasks/{task_id}")
async def api_update_task(
    team_id: str,
    task_id: str,
    req: UpdateTaskReq,
    authorization: Optional[str] = Header(None),
):
    user_id = _require_user_id(authorization)
    result = _call(
        update_team_task,
        user_id=user_id, team_id=team_id, task_id=task_id, done=req.done,
    )
    return _ok(result)


@router.get("/teams/my")
async def api_get_my_teams(authorization: Optional[str] = Header(None)):
    user_id = _require_user_id(authorization)
    result = _call(get_my_teams, user_id=user_id)
    return _ok(result)
