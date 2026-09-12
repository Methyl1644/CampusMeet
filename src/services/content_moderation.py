"""Unified deterministic content-moderation decisions.

This module owns the stable contract consumed by later moderation gates.  It
does not persist decisions or delegate enforcement to an AI service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from services.observability import record_metric
from utils.security import ID_CARD_PATTERN, normalize_for_moderation

ModerationAction = Literal["allow", "revise", "review", "block"]
ModerationRisk = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class ModerationDecision:
    action: ModerationAction
    risk_level: ModerationRisk
    rule_ids: list[str]
    user_message: str
    suggestions: list[str]
    cleaned_text: str


@dataclass(frozen=True)
class ModerationContext:
    surface: str
    user_id: str | None = None
    conversation_id: str | None = None
    contact_unlocked: bool = False
    structured_fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _RuleHit:
    rule_id: str
    action: ModerationAction
    risk_level: ModerationRisk
    suggestion: str


_CONTACT_MASK = "[联系方式已隐藏]"
_ACTION_RANK = {"allow": 0, "revise": 1, "review": 2, "block": 3}
_RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

_PHONE_RE = re.compile(r"(?<!\d)1[3-9](?:[\s\-_.·,，。:：]*\d){9}(?!\d)")
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+\s*@\s*[A-Za-z0-9.\-]+\s*\.\s*[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
_WECHAT_RE = re.compile(
    r"(?:微[\W_]*信(?:号)?|v[\W_]*x|v[\W_]*信|wechat|加[\W_]*(?:v|微))"
    r"[\s:：,，-]*(?:号[\s:：]*)?[A-Za-z][A-Za-z0-9_-]{5,19}",
    re.IGNORECASE,
)
_QQ_RE = re.compile(
    r"q[\W_]*q[\W_]*(?:号[\W_]*)?[1-9](?:[\s\-_.·]*\d){4,11}",
    re.IGNORECASE,
)
_URL_RE = re.compile(
    r"(?:https?\s*:\s*/\s*/|www\s*\.)[A-Za-z0-9][A-Za-z0-9.\-/_%?=&+#]*",
    re.IGNORECASE,
)

_OFF_PLATFORM_RE = re.compile(
    r"(?:扫[\W_]*码|加[\W_]*(?:v|微)(?:信)?|"
    r"去[\W_]*(?:q[\W_]*q|微[\W_]*信|群)|"
    r"(?:q[\W_]*q|微[\W_]*信)[\W_]*群|"
    r"复制[\W_]*链接|浏览器[\W_]*打开)",
    re.IGNORECASE,
)
_PRIVATE_VENUE_RE = re.compile(r"酒店|宾馆|旅馆|民宿|开房|私人房间|房间单独|去我家|去你家")
_DATING_RE = re.compile(r"约会|处对象|找对象|约(?:个|一位|女|男)?同学|陪伴|单独见面|交友")
_PAID_COMPANIONSHIP_RE = re.compile(
    r"(?:付费|有偿|高价|长期)[\W_]{0,4}(?:陪睡|陪伴|约会)|包养|陪睡"
)
_SEXUAL_SOLICITATION_RE = re.compile(r"援交|卖淫|嫖娼|性服务|色情交易|裸聊")
_ILLEGAL_RE = re.compile(
    r"赌博|博彩|外围|毒品|冰毒|大麻交易|摇头丸|伪造.{0,4}(?:证件|证明|学历)|"
    r"假证|假文凭|代考|替考|枪支|弹药|管制刀具|入侵.{0,4}(?:账号|系统)"
)
_FRAUD_RE = re.compile(
    r"刷单.{0,12}(?:垫付|返现|稳赚|佣金)|"
    r"(?:稳赚|包赚|保本).{0,12}(?:投资|理财|返利)|"
    r"(?:投资|理财).{0,12}(?:稳赚|包赚|保本)|"
    r"先交.{0,6}(?:保证金|手续费|押金).{0,8}(?:返还|返现)"
)
_FINANCIAL_REVIEW_RE = re.compile(r"押金|保证金|中介费|手续费|投资|理财|借贷|贷款")
_THREAT_RE = re.compile(
    r"杀(?:了|掉|死)你|弄死你|砍死你|打死你|打断你(?:的)?腿|"
    r"不答应.{0,12}(?:伤害|打|杀|曝光)"
)
_DOXXING_RE = re.compile(r"(?:公布|曝光|人肉|开盒).{0,16}(?:身份证|住址|电话|隐私|个人信息)")
_EXACT_ADDRESS_RE = re.compile(
    r"(?:宿舍|公寓|住址|地址)[\s:：]*[A-Za-z0-9一二三四五六七八九十]+(?:栋|楼|幢)"
    r"(?:[A-Za-z0-9一二三四五六七八九十]+(?:室|号))?"
)
_DISCRIMINATION_RE = re.compile(
    r"(?:只要|仅限|限|不要|拒绝|不招|优先).{0,8}"
    r"(?:男生|男性|女生|女性|美女|帅哥|胖子|矮个子|外地人)|"
    r"(?:长得好看|颜值高|美女|帅哥).{0,8}(?:优先|才要|限定)|"
    r"拒绝.{0,8}(?:胖子|矮个子|丑)"
)
_LEGITIMATE_GENDER_CONTEXT_RE = re.compile(
    r"女子组|男子组|女队员|男队员|女性健康|妇女权益|性别研究|更衣室|住宿安排"
)
_SAFETY_CONTEXT_RE = re.compile(
    r"识别|防范|反诈|安全讲座|警示|提醒|请勿|不要泄露|案例分析|普法"
)


def _flatten_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        values: list[str] = []
        for nested in value.values():
            values.extend(_flatten_values(nested))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for nested in value:
            values.extend(_flatten_values(nested))
        return values
    return [str(value)]


def _is_repetitive_spam(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if re.search(r"[!！?？。,.，]{4,}", compact):
        return True
    return re.search(r"(.{2,12})\1{2,}", compact) is not None


def _mask_matches(text: str, patterns: list[re.Pattern[str]]) -> str:
    cleaned = text
    for pattern in patterns:
        cleaned = pattern.sub(_CONTACT_MASK, cleaned)
    return cleaned


def _add_hit(hits: list[_RuleHit], hit: _RuleHit) -> None:
    if hit.rule_id not in {existing.rule_id for existing in hits}:
        hits.append(hit)


def moderate_content(text: str, context: ModerationContext) -> ModerationDecision:
    """Evaluate text and structured fields using deterministic policy rules."""
    normalized_text = normalize_for_moderation(str(text or ""))
    structured_text = " ".join(
        normalize_for_moderation(value) for value in _flatten_values(context.structured_fields)
    )
    evaluation_text = " ".join(part for part in (normalized_text, structured_text) if part)
    semantic_text = re.sub(r"[\W_]+", "", evaluation_text)
    hits: list[_RuleHit] = []

    contact_patterns = [_PHONE_RE, _EMAIL_RE, _WECHAT_RE, _QQ_RE]
    if not (context.surface == "message" and context.contact_unlocked):
        contact_rules = (
            (_PHONE_RE, "contact.phone"),
            (_EMAIL_RE, "contact.email"),
            (_WECHAT_RE, "contact.wechat"),
            (_QQ_RE, "contact.qq"),
        )
        for pattern, rule_id in contact_rules:
            if pattern.search(evaluation_text):
                _add_hit(
                    hits,
                    _RuleHit(rule_id, "revise", "high", "请删除联系方式，成队后再交换"),
                )

    if (_URL_RE.search(evaluation_text) or _OFF_PLATFORM_RE.search(evaluation_text)) and not (
        context.surface == "message" and context.contact_unlocked
    ):
        _add_hit(
            hits,
            _RuleHit(
                "redirect.off_platform",
                "revise",
                "medium",
                "请在平台内完成沟通，不要引导用户前往站外",
            ),
        )

    private_dating = _PRIVATE_VENUE_RE.search(semantic_text) and _DATING_RE.search(semantic_text)
    if private_dating:
        _add_hit(
            hits,
            _RuleHit(
                "sexual.private_dating",
                "block",
                "critical",
                "平台不支持以私密场所为目的的约会或招募",
            ),
        )
    if _PAID_COMPANIONSHIP_RE.search(semantic_text):
        _add_hit(
            hits,
            _RuleHit(
                "sexual.paid_companionship",
                "block",
                "critical",
                "平台不支持付费陪伴或带有性暗示的招募",
            ),
        )
    if _SEXUAL_SOLICITATION_RE.search(semantic_text):
        _add_hit(
            hits,
            _RuleHit(
                "sexual.solicitation",
                "block",
                "critical",
                "平台禁止发布色情交易或性服务相关内容",
            ),
        )

    safety_context = _SAFETY_CONTEXT_RE.search(semantic_text) is not None
    if _ILLEGAL_RE.search(semantic_text) and not safety_context:
        _add_hit(
            hits,
            _RuleHit("illegal.service", "block", "critical", "平台禁止违法活动或服务"),
        )
    fraud_detected = _FRAUD_RE.search(semantic_text) is not None and not safety_context
    if fraud_detected:
        _add_hit(
            hits,
            _RuleHit("fraud.payment", "block", "critical", "平台禁止欺诈和诱导付款"),
        )
    if _FINANCIAL_REVIEW_RE.search(semantic_text) and not fraud_detected and not safety_context:
        _add_hit(
            hits,
            _RuleHit("risk.financial", "review", "high", "请说明费用用途并等待人工复核"),
        )
    if _THREAT_RE.search(semantic_text):
        _add_hit(
            hits,
            _RuleHit("threat.violence", "block", "critical", "平台禁止威胁或暴力内容"),
        )

    has_identity_number = ID_CARD_PATTERN.search(evaluation_text) is not None
    if has_identity_number or _DOXXING_RE.search(semantic_text) or _EXACT_ADDRESS_RE.search(semantic_text):
        _add_hit(
            hits,
            _RuleHit("privacy.identity", "block", "critical", "请勿发布身份证、住址等个人隐私"),
        )

    if _DISCRIMINATION_RE.search(semantic_text) and not _LEGITIMATE_GENDER_CONTEXT_RE.search(
        semantic_text
    ):
        _add_hit(
            hits,
            _RuleHit(
                "discrimination.recruitment",
                "revise",
                "high",
                "请删除与活动无关的性别、外貌或身份限制",
            ),
        )

    if _is_repetitive_spam(evaluation_text):
        _add_hit(
            hits,
            _RuleHit("spam.repetitive", "revise", "medium", "请精简重复或营销式内容"),
        )

    cleaned_text = normalized_text
    if not (context.surface == "message" and context.contact_unlocked):
        cleaned_text = _mask_matches(cleaned_text, contact_patterns)
    if has_identity_number:
        cleaned_text = ID_CARD_PATTERN.sub("[身份证号已隐藏]", cleaned_text)

    if not hits:
        decision = ModerationDecision(
            action="allow",
            risk_level="low",
            rule_ids=[],
            user_message="内容审核通过",
            suggestions=[],
            cleaned_text=cleaned_text,
        )
        record_metric("moderation.decisions", surface=context.surface, action=decision.action)
        return decision

    strongest_action = max(hits, key=lambda hit: _ACTION_RANK[hit.action]).action
    strongest_risk = max(hits, key=lambda hit: _RISK_RANK[hit.risk_level]).risk_level
    messages = {
        "revise": "内容包含不适合公开发布的信息，请修改后重试",
        "review": "内容需要人工复核，请暂勿发布",
        "block": "内容涉及平台禁止的高风险行为，无法发布",
    }
    decision = ModerationDecision(
        action=strongest_action,
        risk_level=strongest_risk,
        rule_ids=[hit.rule_id for hit in hits],
        user_message=messages[strongest_action],
        suggestions=list(dict.fromkeys(hit.suggestion for hit in hits)),
        cleaned_text=cleaned_text,
    )
    record_metric("moderation.decisions", surface=context.surface, action=decision.action)
    return decision
