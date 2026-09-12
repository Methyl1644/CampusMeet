"""AI 工具：对话式发帖、分类审核、队友匹配、成队规划

使用 LLM 直接实现 AI 功能，后续裴斐提供 Coze 工作流 ID 后可切换为 Coze 调用。
"""
import os
import json
import logging
from typing import Any
from urllib.parse import urlparse
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
from services.observability import record_metric
from tools.auth_tools import _user_brief, _user_to_dict
from services.content import OPTIONAL_POST_FIELDS, POST_FIELDS, build_post_draft
from services.tag_governance import sanitize_unknown_concepts
from services.moderation_cases import has_active_restriction, users_are_blocked
from utils.security import screen_content

logger = logging.getLogger(__name__)

MODEL_ID = "doubao-seed-2-0-pro-260215"
COZE_DEPLOY_TIMEOUT_SECONDS = 15
COZE_LEGACY_TIMEOUT_SECONDS = 25
COZE_CHAINED_LEGACY_TIMEOUT_SECONDS = 7
COZE_POST_DRAFT_CANDIDATE_LIMIT = 20
MAIN_CATEGORIES = {"竞赛与项目", "学习与科研", "体育与健身", "旅行与户外", "校园生活", "拼团与AA"}
TAG_CATEGORIES = {"activity", "skill", "role", "level", "audience"}
RISK_LEVELS = {"low", "medium", "high"}
POST_DRAFT_KEYS = {
    "activity_name",
    "target_members",
    "needed_roles",
    "weekly_hours",
    "school_scope",
    "deadline",
    "description",
}


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


def _try_coze_workflow(
    workflow_env_key: str,
    parameters: dict,
    timeout: int = COZE_LEGACY_TIMEOUT_SECONDS,
) -> dict | None:
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
            timeout=timeout,
        )
        data = resp.json()
        if data.get("code") == 0:
            return json.loads(data.get("data", "{}")) if isinstance(data.get("data"), str) else data.get("data")
    except Exception as e:
        logger.warning(f"Coze workflow {workflow_env_key} call failed: {e}")
    return None


def _unwrap_coze_result(value) -> dict | None:
    """Extract a workflow result from common Coze deployment response wrappers."""
    result_fields = {
        "reply",
        "draft",
        "is_complete",
        "field_states",
        "suggested_tag_ids",
        "main_category",
        "tag_ids",
        "risk_level",
        "matches",
        "division_of_labor",
        "meeting_agenda",
        "task_list",
        "risk_reminders",
    }
    current = value
    for _ in range(5):
        if isinstance(current, str):
            try:
                current = json.loads(current)
            except json.JSONDecodeError:
                return None
        if not isinstance(current, dict):
            return None
        if result_fields.intersection(current):
            return current
        for wrapper_key in ("data", "output", "result"):
            if wrapper_key in current:
                current = current[wrapper_key]
                break
        else:
            return None
    return None


def _try_coze_deployed_api(api_url_env_key: str, parameters: dict) -> dict | None:
    """Call a deployed coze.site workflow when its URL and token are configured."""
    api_url = os.getenv(api_url_env_key, "").strip()
    token = os.getenv("COZE_DEPLOY_API_TOKEN", "").strip()
    if not api_url or not token:
        record_metric("coze.calls", workflow=api_url_env_key, result="not_configured")
        return None
    parsed_url = urlparse(api_url)
    hostname = (parsed_url.hostname or "").lower()
    if (
        parsed_url.scheme != "https"
        or not hostname.endswith(".coze.site")
        or parsed_url.path.rstrip("/") != "/run"
        or parsed_url.username
        or parsed_url.password
    ):
        logger.warning("Rejected invalid Coze deployment URL in %s", api_url_env_key)
        record_metric("coze.calls", workflow=api_url_env_key, result="invalid_url")
        return None
    try:
        import requests
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=parameters,
            timeout=COZE_DEPLOY_TIMEOUT_SECONDS,
        )
        if callable(getattr(resp, "raise_for_status", None)):
            resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict) and payload.get("code") not in (None, 0):
            logger.warning("Coze deployed API %s returned code %s", api_url_env_key, payload.get("code"))
            record_metric("coze.calls", workflow=api_url_env_key, result="provider_error")
            return None
        record_metric("coze.calls", workflow=api_url_env_key, result="success")
        return _unwrap_coze_result(payload)
    except Exception as e:
        logger.warning("Coze deployed API %s call failed: %s", api_url_env_key, e)
        record_metric("coze.calls", workflow=api_url_env_key, result="timeout_or_error")
        return None


def _valid_post_draft_result(
    result: dict | None,
    allowed_ids: set[str] | None,
    kind: str = "",
) -> bool:
    if not isinstance(result, dict):
        return False
    if not (
        isinstance(result.get("reply"), str)
        and len(result["reply"]) <= 500
        and isinstance(result.get("draft"), dict)
        and isinstance(result.get("is_complete"), bool)
        and isinstance(result.get("field_states"), dict)
        and isinstance(result.get("suggested_tag_ids"), list)
    ):
        return False
    draft = result["draft"]
    if kind in POST_FIELDS:
        draft_valid = bool(
            set(draft) == POST_DRAFT_KEYS
            and isinstance(draft.get("activity_name"), str)
            and isinstance(draft.get("target_members"), int)
            and not isinstance(draft.get("target_members"), bool)
            and draft["target_members"] >= 0
            and isinstance(draft.get("needed_roles"), list)
            and all(isinstance(role, str) for role in draft["needed_roles"])
            and len(draft["needed_roles"]) == len(set(draft["needed_roles"]))
            and all(
                isinstance(draft.get(field), str)
                for field in ("weekly_hours", "school_scope", "deadline", "description")
            )
        )
        if not draft_valid:
            return False

    valid_statuses = {"confirmed", "none", "unknown", "skipped", "pending"}
    fields_valid = all(
        isinstance(value, dict)
        and "value" in value
        and value.get("status") in valid_statuses
        for value in result["field_states"].values()
    )
    if kind in POST_FIELDS:
        fields_valid = fields_valid and set(result["field_states"]) == set(POST_FIELDS[kind])
        if fields_valid:
            required_fields = [field for field in POST_FIELDS[kind] if field != "description"]
            pending_fields = [
                field
                for field in required_fields
                if result["field_states"][field]["status"] == "pending"
            ]
            if result["is_complete"] != (not pending_fields):
                return False
            if "missing_fields" in result and result["missing_fields"] != pending_fields:
                return False
            if "next_field" in result:
                reported_next = result["next_field"]
                if reported_next in ("", {}, []):
                    reported_next = None
                expected_next = pending_fields[0] if pending_fields else None
                if reported_next != expected_next:
                    return False
            for field in required_fields:
                if result["field_states"][field]["status"] != "confirmed":
                    continue
                value = draft[field]
                if value in ("", None, [], 0):
                    return False
    tag_ids = result["suggested_tag_ids"]
    tags_valid = (
        len(tag_ids) <= 4
        and all(isinstance(tag_id, str) for tag_id in tag_ids)
        and len(tag_ids) == len(set(tag_ids))
        and (allowed_ids is None or all(tag_id in allowed_ids for tag_id in tag_ids))
    )
    next_field = result.get("next_field")
    next_field_valid = next_field is None or isinstance(next_field, str) or next_field in ({}, [])
    missing_fields = result.get("missing_fields", [])
    missing_fields_valid = (
        isinstance(missing_fields, list)
        and all(isinstance(field, str) for field in missing_fields)
        and len(missing_fields) == len(set(missing_fields))
    )
    degraded_valid = "degraded" not in result or isinstance(result["degraded"], bool)
    return fields_valid and tags_valid and next_field_valid and missing_fields_valid and degraded_valid


def _valid_classify_result(result: dict | None, allowed_ids: set[str]) -> bool:
    if not isinstance(result, dict):
        return False
    tag_ids = result.get("tag_ids")
    concepts = result.get("unknown_concepts")
    suggestions = result.get("suggestions")
    return bool(
        result.get("main_category") in MAIN_CATEGORIES
        and result.get("risk_level") in RISK_LEVELS
        and isinstance(tag_ids, list)
        and len(tag_ids) <= 8
        and all(isinstance(tag_id, str) and tag_id in allowed_ids for tag_id in tag_ids)
        and len(tag_ids) == len(set(tag_ids))
        and isinstance(concepts, list)
        and len(concepts) <= 5
        and all(
            isinstance(concept, dict)
            and isinstance(concept.get("name"), str)
            and 2 <= len(concept["name"]) <= 30
            and concept.get("category") in TAG_CATEGORIES
            and isinstance(concept.get("reason"), str)
            and len(concept["reason"]) <= 200
            for concept in concepts
        )
        and isinstance(suggestions, list)
        and len(suggestions) <= 5
        and all(isinstance(suggestion, str) and len(suggestion) <= 200 for suggestion in suggestions)
    )


def _sanitize_external_value(value):
    if isinstance(value, str):
        return screen_content(value).cleaned_text
    if isinstance(value, list):
        return [_sanitize_external_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_external_value(item) for key, item in value.items()}
    return value


def _validated_matches(result: dict | None, allowed_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(result, dict) or not isinstance(result.get("matches"), list):
        return []
    matches = []
    seen = set()
    for raw in result["matches"]:
        if not isinstance(raw, dict):
            continue
        user_id = str(raw.get("user_id") or "")
        if user_id not in allowed_ids or user_id in seen:
            continue
        try:
            score = int(round(float(raw.get("score", 0))))
        except (TypeError, ValueError):
            continue
        reason = str(raw.get("reason") or "").strip()[:200]
        if not reason:
            continue
        seen.add(user_id)
        matches.append(
            {"user_id": user_id, "score": min(100, max(0, score)), "reason": reason}
        )
    return sorted(matches, key=lambda item: (-item["score"], item["user_id"]))[:5]


def _deterministic_matches(post: Post, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    desired = {str(item).strip().casefold() for item in (post.needed_roles or []) if str(item).strip()}
    ranked = []
    for candidate in candidates:
        skills = {str(item).strip().casefold() for item in candidate.get("skills", []) if str(item).strip()}
        overlap = len(desired.intersection(skills))
        score = min(95, 60 + overlap * 15 + min(len(skills), 5) * 2)
        reason = "候选人的公开技能与组队需求匹配"
        ranked.append({"user_id": str(candidate["user_id"]), "score": score, "reason": reason})
    return sorted(ranked, key=lambda item: (-item["score"], item["user_id"]))[:5]


def _validated_team_plan(
    result: dict | None,
    allowed_member_ids: set[str],
) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    required = ("division_of_labor", "meeting_agenda", "task_list", "risk_reminders")
    if not all(isinstance(result.get(key), list) for key in required):
        return None

    division = []
    for item in result["division_of_labor"][:20]:
        if not isinstance(item, dict):
            continue
        member_id = str(item.get("member_id") or "")
        role = str(item.get("role") or "").strip()[:80]
        responsibilities = str(item.get("responsibilities") or "").strip()[:500]
        if member_id in allowed_member_ids and role and responsibilities:
            division.append(
                {
                    "role": role,
                    "responsibilities": responsibilities,
                    "member_id": member_id,
                }
            )

    agenda = []
    agenda_ids = set()
    for item in result["meeting_agenda"][:20]:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()[:64]
        content = str(item.get("content") or "").strip()[:500]
        if item_id and content and item_id not in agenda_ids:
            agenda_ids.add(item_id)
            agenda.append({"id": item_id, "content": content, "done": bool(item.get("done", False))})

    tasks = []
    task_ids = set()
    for item in result["task_list"][:50]:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()[:64]
        title = str(item.get("title") or "").strip()[:120]
        if not item_id or not title or item_id in task_ids:
            continue
        assignee_id = item.get("assignee_id")
        if assignee_id not in (None, "") and str(assignee_id) not in allowed_member_ids:
            assignee_id = None
        task = {"id": item_id, "title": title, "done": bool(item.get("done", False))}
        if assignee_id not in (None, ""):
            task["assignee_id"] = str(assignee_id)
        if item.get("due_at"):
            task["due_at"] = str(item["due_at"])[:40]
        task_ids.add(item_id)
        tasks.append(task)

    reminders = [
        str(item).strip()[:300]
        for item in result["risk_reminders"][:10]
        if isinstance(item, str) and item.strip()
    ]
    return {
        "division_of_labor": division,
        "meeting_agenda": agenda,
        "task_list": tasks,
        "risk_reminders": reminders,
    }


def _deterministic_team_plan(
    team: Team,
    members: list[dict[str, Any]],
    post_info: dict[str, Any],
) -> dict[str, Any]:
    division = [
        {
            "role": item.get("suggested_role") or "团队成员",
            "responsibilities": "根据团队目标完成分配的工作",
            "member_id": str(item["user_id"]),
        }
        for item in members
    ]
    activity = str(post_info.get("activity_name") or team.activity_name)
    return {
        "division_of_labor": division,
        "meeting_agenda": [
            {"id": "a1", "content": f"确认{activity}目标与时间节点", "done": False},
            {"id": "a2", "content": "确认成员分工和沟通方式", "done": False},
        ],
        "task_list": [
            {"id": "t1", "title": "确认赛程或活动要求", "done": False},
            {"id": "t2", "title": "制定第一阶段计划", "done": False},
            {"id": "t3", "title": "安排首次团队会议", "done": False},
        ],
        "risk_reminders": ["及时确认截止时间", "重要决策在团队内留存记录"],
    }


def _local_draft_made_progress(
    kind: str,
    previous_fields: dict[str, Any],
    result: dict[str, Any],
) -> bool:
    returned_fields = result.get("field_states", {})
    for field in POST_FIELDS[kind]:
        previous = previous_fields.get(field)
        previous_status = (
            previous.get("status")
            if isinstance(previous, dict)
            else ("none" if field in OPTIONAL_POST_FIELDS else "pending")
        )
        previous_value = (
            previous.get("value")
            if isinstance(previous, dict) and previous_status == "confirmed"
            else None
        )
        current = returned_fields.get(field)
        if not isinstance(current, dict):
            continue
        if current.get("status") != previous_status or current.get("value") != previous_value:
            return True
    return False


@tool
def ai_post_draft(
    message: str,
    draft: str = "",
    user_skills: str = "",
    kind: str = "",
    field_states: str = "",
    candidate_tags: str = "",
    topic_id: str = "",
) -> str:
    """AI 对话式发帖助手。用户输入一句话描述组队需求，AI 追问缺失信息并生成结构化草稿。message 为用户输入，draft 为当前草稿(JSON字符串)，user_skills 为用户技能(逗号分隔)。返回追问回复和结构化草稿。"""
    ctx = request_context.get() or new_context(method="ai_post_draft")

    parsed_fields = json.loads(field_states) if field_states else {}
    parsed_candidates = json.loads(candidate_tags) if candidate_tags else []
    local_result = None
    if kind in POST_FIELDS:
        local_result = build_post_draft(
            kind=kind,
            message=message,
            previous_fields=parsed_fields,
            candidates=parsed_candidates,
        )
        if _local_draft_made_progress(kind, parsed_fields, local_result):
            local_result["degraded"] = False
            return json.dumps(local_result, ensure_ascii=False)

    model_candidates = parsed_candidates[:COZE_POST_DRAFT_CANDIDATE_LIMIT]
    coze_params = {
        "message": screen_content(message).cleaned_text,
        "draft": screen_content(draft).cleaned_text,
        "user_skills": screen_content(user_skills).cleaned_text,
        "kind": kind,
        "field_states": {
            field_name: {
                **state,
                "value": _sanitize_external_value(state.get("value")),
            }
            if isinstance(state, dict)
            else state
            for field_name, state in parsed_fields.items()
        },
        "candidate_tags": model_candidates,
        "topic_id": topic_id or "",
    }
    allowed_ids = (
        {str(item.get("tag_id")) for item in parsed_candidates if isinstance(item, dict)}
        if kind
        else None
    )
    deployed_configured = bool(
        os.getenv("COZE_POST_DRAFT_API_URL", "").strip()
        and os.getenv("COZE_DEPLOY_API_TOKEN", "").strip()
    )
    coze_result = _try_coze_deployed_api("COZE_POST_DRAFT_API_URL", coze_params)
    if coze_result and not _valid_post_draft_result(coze_result, allowed_ids, kind):
        logger.warning("Coze deployed post-draft output failed controlled-schema validation")
        coze_result = None
    if not coze_result and not deployed_configured:
        legacy_timeout = COZE_CHAINED_LEGACY_TIMEOUT_SECONDS if deployed_configured else COZE_LEGACY_TIMEOUT_SECONDS
        coze_result = _try_coze_workflow("COZE_WORKFLOW_POST_DRAFT", coze_params, timeout=legacy_timeout)
        if coze_result and not _valid_post_draft_result(coze_result, allowed_ids, kind):
            logger.warning("Legacy Coze post-draft output failed controlled-schema validation")
            coze_result = None
    if coze_result:
        if kind in POST_FIELDS:
            pending_fields = [
                field
                for field in POST_FIELDS[kind]
                if field != "description"
                and coze_result["field_states"][field]["status"] == "pending"
            ]
            coze_result = {
                **coze_result,
                "candidate_tags": parsed_candidates,
                "next_field": pending_fields[0] if pending_fields else None,
                "missing_fields": pending_fields,
            }
        elif coze_result.get("next_field") in ("", {}, []):
            coze_result = {**coze_result, "next_field": None}
        if kind:
            returned_ids = coze_result.get("suggested_tag_ids", [])
            returned_fields = coze_result.get("field_states", {})
            valid_statuses = {"confirmed", "none", "unknown", "skipped", "pending"}
            fields_valid = isinstance(returned_fields, dict) and all(
                isinstance(value, dict) and value.get("status") in valid_statuses
                for value in returned_fields.values()
            )
            tags_valid = isinstance(returned_ids, list) and all(str(tag_id) in allowed_ids for tag_id in returned_ids)
            if fields_valid and tags_valid:
                return json.dumps(coze_result, ensure_ascii=False)
            logger.warning("Coze post-draft output failed controlled-schema validation")
        else:
            return json.dumps(coze_result, ensure_ascii=False)

    if kind:
        return json.dumps(local_result, ensure_ascii=False)

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
def ai_classify_review(post_title: str, post_description: str, candidate_tags: str = "") -> str:
    """AI 分类与审核。自动对帖子进行分类、打标签、评估风险等级，并给出修改建议。post_title 为帖子标题，post_description 为帖子描述。"""
    ctx = request_context.get() or new_context(method="ai_classify_review")

    # 先尝试 Coze 工作流
    parsed_candidates = json.loads(candidate_tags) if candidate_tags else []
    candidate_ids = {str(item.get("tag_id")) for item in parsed_candidates if isinstance(item, dict)}
    coze_params = {
        "title": screen_content(post_title).cleaned_text,
        "description": screen_content(post_description).cleaned_text,
        "candidate_tags": parsed_candidates,
    }
    deployed_configured = bool(
        os.getenv("COZE_CLASSIFY_REVIEW_API_URL", "").strip()
        and os.getenv("COZE_DEPLOY_API_TOKEN", "").strip()
    )
    coze_result = _try_coze_deployed_api("COZE_CLASSIFY_REVIEW_API_URL", coze_params)
    if coze_result and not _valid_classify_result(coze_result, candidate_ids):
        logger.warning("Coze deployed classify-review output failed controlled-schema validation")
        coze_result = None
    if not coze_result:
        legacy_timeout = COZE_CHAINED_LEGACY_TIMEOUT_SECONDS if deployed_configured else COZE_LEGACY_TIMEOUT_SECONDS
        coze_result = _try_coze_workflow("COZE_WORKFLOW_CLASSIFY_REVIEW", coze_params, timeout=legacy_timeout)
        if coze_result and not _valid_classify_result(coze_result, candidate_ids):
            logger.warning("Legacy Coze classify-review output failed controlled-schema validation")
            coze_result = None
    if coze_result:
        if candidate_tags:
            tag_ids = coze_result.get("tag_ids", [])
            coze_result["tag_ids"] = (
                list(dict.fromkeys(str(tag_id) for tag_id in tag_ids if str(tag_id) in candidate_ids))[:8]
                if isinstance(tag_ids, list)
                else []
            )
            coze_result["unknown_concepts"] = sanitize_unknown_concepts(
                coze_result.get("unknown_concepts")
            )
            return json.dumps(coze_result, ensure_ascii=False)
        else:
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
  "unknown_concepts": [{"name": "库中缺少的可复用概念", "category": "activity/skill/role/level/audience", "reason": "判断理由"}],
  "risk_level": "low/medium/high",
  "suggestions": ["修改建议1", "修改建议2"]
}"""

    user_msg = f"帖子标题: {post_title}\n帖子描述: {post_description}"
    try:
        result_text = _call_llm(system_prompt, user_msg, temperature=0.3)
        result = json.loads(result_text)
        if candidate_tags:
            names_to_ids = {
                str(item.get("canonical_name")): str(item.get("tag_id"))
                for item in parsed_candidates
                if isinstance(item, dict)
            }
            result["tag_ids"] = [
                names_to_ids[name]
                for name in result.get("tags", [])
                if isinstance(name, str) and name in names_to_ids
            ][:4]
            result.pop("tags", None)
            result["unknown_concepts"] = sanitize_unknown_concepts(result.get("unknown_concepts"))
        return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        fallback = {
            "main_category": "校园生活",
            "risk_level": "low",
            "suggestions": ["自动分类失败，请手动设置分类"],
        }
        fallback["tag_ids" if candidate_tags else "tags"] = []
        return json.dumps(fallback, ensure_ascii=False)
    except Exception as e:
        logger.error(f"ai_classify_review error: {e}")
        return json.dumps({"error": f"AI 审核失败: {str(e)}"}, ensure_ascii=False)


@tool
def ai_match_teammates(post_id: str) -> str:
    """AI 智能匹配。根据帖子所需角色，从数据库中匹配合适的队友，输出匹配分数和推荐理由。post_id 为帖子ID。"""
    ctx = request_context.get() or new_context(method="ai_match_teammates")
    try:
        session = get_session()
        try:
            pid = int(post_id)
            post = session.execute(select(Post).where(Post.id == pid)).scalar_one_or_none()
            if not post:
                return json.dumps({"success": False, "message": "帖子不存在"}, ensure_ascii=False)

            users = session.execute(
                select(User)
                .where(User.auth_status != "unverified")
                .where(User.id != post.author_id)
            ).scalars().all()
            candidates = [
                user
                for user in users
                if not users_are_blocked(session, post.author_id, user.id)
                and not has_active_restriction(session, user.id, "all_interactions")
            ][:20]
            if not candidates:
                return json.dumps({"success": True, "matches": [], "message": "暂无可匹配的用户"}, ensure_ascii=False)
            needed_roles = post.needed_roles or []
            candidate_info = []
            for u in candidates:
                candidate_info.append({
                    "user_id": str(u.id),
                    "nickname": u.nickname,
                    "major": u.major,
                    "grade": u.grade,
                    "skills": u.skills or [],
                })

            controlled_context = {
                "post": {
                    "post_id": str(post.id),
                    "title": post.title,
                    "activity_name": post.activity_name,
                    "main_category": post.main_category,
                    "needed_roles": needed_roles,
                    "description": post.description or "",
                },
                "candidates": candidate_info,
            }
            coze_result = _try_coze_deployed_api("COZE_MATCH_API_URL", controlled_context)
            if coze_result is None:
                coze_result = _try_coze_workflow("COZE_WORKFLOW_MATCH", controlled_context)

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

按分数从高到低排序，最多返回5个。只能返回候选列表中的用户ID。"""
            if coze_result is None:
                try:
                    coze_result = json.loads(
                        _call_llm(
                            system_prompt,
                            json.dumps(controlled_context, ensure_ascii=False),
                            temperature=0.3,
                        )
                    )
                except Exception as exc:
                    logger.warning("Match semantic provider unavailable; using deterministic ranking: %s", exc)

            allowed_ids = {str(item["user_id"]) for item in candidate_info}
            matches = _validated_matches(coze_result, allowed_ids)
            if not matches:
                matches = _deterministic_matches(post, candidate_info)
            return json.dumps({"success": True, "matches": matches}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"ai_match_teammates error: {e}")
        return json.dumps({"success": False, "message": f"匹配失败: {str(e)}"}, ensure_ascii=False)


@tool
def ai_team_plan(team_id: str) -> str:
    """AI 成队规划。根据团队成员能力生成分工建议、首次会议议程、任务清单和风险提醒。team_id 为团队ID。"""
    ctx = request_context.get() or new_context(method="ai_team_plan")

    try:
        session = get_session()
        try:
            tid = int(team_id)
            team = session.execute(select(Team).where(Team.id == tid)).scalar_one_or_none()
            if not team:
                return json.dumps({"success": False, "message": "团队不存在"}, ensure_ascii=False)

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

            post = session.execute(select(Post).where(Post.id == team.post_id)).scalar_one_or_none()
            post_info = {
                "activity_name": team.activity_name,
                "needed_roles": post.needed_roles if post else [],
                "description": post.description if post else "",
            }
            controlled_context = {
                "team": {
                    "team_id": str(team.id),
                    "activity_name": team.activity_name,
                    "existing_tasks": team.task_list or [],
                },
                "post": post_info,
                "members": member_info,
            }
            result = _try_coze_deployed_api("COZE_TEAM_PLAN_API_URL", controlled_context)
            if result is None:
                result = _try_coze_workflow("COZE_WORKFLOW_TEAM_PLAN", controlled_context)

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

            if result is None:
                try:
                    result = json.loads(
                        _call_llm(
                            system_prompt,
                            json.dumps(controlled_context, ensure_ascii=False),
                            temperature=0.5,
                        )
                    )
                except Exception as exc:
                    logger.warning("Team-plan semantic provider unavailable; using deterministic plan: %s", exc)
                    result = None
            allowed_member_ids = {str(item["user_id"]) for item in member_info}
            result = _validated_team_plan(result, allowed_member_ids)
            if result is None:
                result = _deterministic_team_plan(team, member_info, post_info)
            team.division_of_labor = result.get("division_of_labor", [])
            team.meeting_agenda = result.get("meeting_agenda", [])
            team.task_list = result.get("task_list", [])
            team.risk_reminders = result.get("risk_reminders", [])
            session.commit()

            return json.dumps({"success": True, "team_plan": result, "message": "AI 成队规划已生成并保存"}, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"ai_team_plan error: {e}")
        return json.dumps({"success": False, "message": f"成队规划失败: {str(e)}"}, ensure_ascii=False)
