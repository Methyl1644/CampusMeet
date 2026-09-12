from typing import Any

from fastapi import APIRouter, Depends

from api.common import current_user_id, invoke_tool, parse_tool_result
from api.schemas.collaboration import MessageSendRequest
from tools.message_tools import close_conversation, confirm_team, get_conversations, get_messages, send_message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/conversations")
def conversations(
    page: int = 1,
    page_size: int = 20,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            get_conversations,
            {"user_id": user_id, "page": page, "page_size": page_size},
        )
    )


@router.get("/{conversation_id}")
def messages(
    conversation_id: str,
    page: int = 1,
    page_size: int = 50,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    return parse_tool_result(
        invoke_tool(
            get_messages,
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "page": page,
                "page_size": page_size,
            },
        )
    )


@router.post("/{conversation_id}/send")
def send(conversation_id: str, body: MessageSendRequest, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    if isinstance(body, MessageSendRequest):
        body = body.model_dump()
    return parse_tool_result(
        invoke_tool(send_message, {"user_id": user_id, "conversation_id": conversation_id, "content": body.get("content", "")}),
        "message",
    )


@router.post("/{conversation_id}/confirm-team")
def confirm(conversation_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(confirm_team, {"user_id": user_id, "conversation_id": conversation_id}))
    result["data"] = {"confirmed": True, **result["data"]}
    return result


@router.post("/{conversation_id}/close")
def close(conversation_id: str, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    result = parse_tool_result(invoke_tool(close_conversation, {"user_id": user_id, "conversation_id": conversation_id}))
    result["data"] = {"closed": True, **result["data"]}
    return result
