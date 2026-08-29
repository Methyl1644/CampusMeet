"""CampusMate AI 后端智能体

角色 C — 后端与安全
负责：用户认证、帖子管理、申请处理、消息聊天、团队管理
"""
import os
import json
from typing import Annotated
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain_openai import ChatOpenAI
from langchain.messages import ToolMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver

# 工具导入
from tools.auth_tools import (
    register_auth_send_code,
    register_user,
    login_user,
    verify_campus_email,
    get_user_profile,
    update_user_profile,
)
from tools.post_tools import (
    create_post,
    list_posts,
    get_post_detail,
    get_my_posts,
)
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
from tools.team_tools import (
    get_team_detail,
    update_team_task,
    get_my_teams,
)
from tools.security_tools import screen_text_content
from tools.ai_tools import (
    ai_post_draft,
    ai_classify_review,
    ai_match_teammates,
    ai_team_plan,
)

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40


def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore


class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]


# 所有工具列表
ALL_TOOLS = [
    register_auth_send_code,
    register_user,
    login_user,
    verify_campus_email,
    get_user_profile,
    update_user_profile,
    create_post,
    list_posts,
    get_post_detail,
    get_my_posts,
    create_application,
    get_applications,
    accept_application,
    reject_application,
    get_my_applications,
    get_conversations,
    get_messages,
    send_message,
    confirm_team,
    close_conversation,
    get_team_detail,
    update_team_task,
    get_my_teams,
    # 安全工具
    screen_text_content,
    # AI 工具
    ai_post_draft,
    ai_classify_review,
    ai_match_teammates,
    ai_team_plan,
]


@wrap_tool_call
def handle_tool_errors(request, handler):
    """工具执行错误处理中间件"""
    try:
        return handler(request)
    except Exception as e:
        return ToolMessage(
            content=f"工具执行错误: ({str(e)})",
            tool_call_id=request.tool_call["id"],
        )


def build_agent(ctx=None):
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    llm = ChatOpenAI(
        model=cfg["config"].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg["config"].get("temperature", 0.7),
        streaming=True,
        timeout=cfg["config"].get("timeout", 600),
        extra_body={
            "thinking": {
                "type": cfg["config"].get("thinking", "disabled"),
            }
        },
        default_headers=default_headers(ctx) if ctx else {},
    )

    return create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=ALL_TOOLS,
        middleware=[handle_tool_errors],
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
