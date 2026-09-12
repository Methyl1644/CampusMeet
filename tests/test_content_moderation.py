from dataclasses import asdict

import pytest

from services.content_moderation import (
    ModerationContext,
    ModerationDecision,
    moderate_content,
)
from utils.security import ScreenResult, screen_content


def context(**overrides: object) -> ModerationContext:
    values = {
        "surface": "post",
        "user_id": "42",
        "conversation_id": None,
        "contact_unlocked": False,
        "structured_fields": {},
    }
    values.update(overrides)
    return ModerationContext(**values)


def test_decision_contract_is_stable() -> None:
    decision = moderate_content("周日下午在体育馆打羽毛球", context())

    assert isinstance(decision, ModerationDecision)
    assert asdict(decision) == {
        "action": "allow",
        "risk_level": "low",
        "rule_ids": [],
        "user_message": "内容审核通过",
        "suggestions": [],
        "cleaned_text": "周日下午在体育馆打羽毛球",
    }


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("手机：１３８ ００１３ ８０００", "contact.phone"),
        ("微。信 abc_12345", "contact.wechat"),
        ("V X：campus_2026", "contact.wechat"),
        ("Q Q 号 12345678", "contact.qq"),
        ("邮箱 test＠nju．edu．cn", "contact.email"),
    ],
)
def test_normalizes_full_width_spacing_and_split_contact_details(text: str, rule_id: str) -> None:
    decision = moderate_content(text, context())

    assert decision.action == "revise"
    assert decision.risk_level == "high"
    assert rule_id in decision.rule_ids
    assert "联系方式已隐藏" in decision.cleaned_text


@pytest.mark.parametrize(
    "text",
    [
        "这里不方便说，去 q q 群聊",
        "扫。码进群后联系",
        "复制链接 https：／／example．com／join 到浏览器",
        "加 v 后详谈",
    ],
)
def test_detects_off_platform_redirection(text: str) -> None:
    decision = moderate_content(text, context())

    assert decision.action == "revise"
    assert decision.risk_level in {"medium", "high"}
    assert "redirect.off_platform" in decision.rule_ids


def test_contact_details_are_allowed_only_after_chat_contact_unlock() -> None:
    locked = moderate_content(
        "我的手机号是 13800138000",
        context(surface="message", conversation_id="7"),
    )
    unlocked = moderate_content(
        "我的手机号是 13800138000",
        context(surface="message", conversation_id="7", contact_unlocked=True),
    )

    assert locked.action == "revise"
    assert "contact.phone" in locked.rule_ids
    assert unlocked.action == "allow"
    assert unlocked.rule_ids == []


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("去酒店开房约会，只限女同学", "sexual.private_dating"),
        ("付费陪睡，可长期包养", "sexual.paid_companionship"),
        ("招募援交，价格私聊", "sexual.solicitation"),
        ("出售假证并提供替考", "illegal.service"),
        ("刷单垫付，稳赚返现", "fraud.payment"),
        ("不答应我就打断你的腿", "threat.violence"),
        ("公布他的身份证 320102199001011234", "privacy.identity"),
    ],
)
def test_blocks_explicit_critical_harm(text: str, rule_id: str) -> None:
    decision = moderate_content(text, context())

    assert decision.action == "block"
    assert decision.risk_level == "critical"
    assert rule_id in decision.rule_ids
    assert decision.user_message


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("赌。博组局，今晚开始", "illegal.service"),
        ("刷。单先垫付，保证稳 赚返现", "fraud.payment"),
        ("不答应我就打 断 你 的 腿", "threat.violence"),
        ("只 要 女 生，颜值高优先", "discrimination.recruitment"),
    ],
)
def test_split_punctuation_cannot_bypass_harm_rules(text: str, rule_id: str) -> None:
    decision = moderate_content(text, context())

    assert rule_id in decision.rule_ids
    assert decision.action in {"revise", "block"}


def test_ambiguous_financial_requirement_enters_manual_review() -> None:
    decision = moderate_content("报名需先交200元押金，活动结束后退还", context())

    assert decision.action == "review"
    assert decision.risk_level == "high"
    assert "risk.financial" in decision.rule_ids


def test_private_venue_and_dating_intent_escalate_as_a_combination() -> None:
    venue_only = moderate_content("比赛选手统一入住学校安排的酒店", context())
    dating_only = moderate_content("校园交友活动，公开场地见面", context())
    combined = moderate_content("约女同学到宾馆房间单独见面", context())

    assert venue_only.action == "allow"
    assert dating_only.action in {"allow", "review"}
    assert combined.action == "block"
    assert combined.risk_level == "critical"
    assert "sexual.private_dating" in combined.rule_ids


@pytest.mark.parametrize(
    "text",
    [
        "只要女生，长得好看的优先",
        "拒绝胖子和矮个子报名",
        "限男性参加编程比赛",
    ],
)
def test_requires_revision_for_gender_or_appearance_discrimination(text: str) -> None:
    decision = moderate_content(text, context())

    assert decision.action == "revise"
    assert decision.risk_level == "high"
    assert "discrimination.recruitment" in decision.rule_ids


@pytest.mark.parametrize(
    "text",
    [
        "女子篮球队招募女队员，参加校女子组联赛",
        "女性健康讲座面向全校女生开放",
        "酒店管理专业开展住宿安全讲座，请勿泄露身份证信息",
        "网络安全社团讲解如何识别刷单诈骗，不收取任何费用",
    ],
)
def test_allows_legitimate_contextual_counterexamples(text: str) -> None:
    decision = moderate_content(text, context())

    assert decision.action == "allow"
    assert decision.risk_level == "low"
    assert decision.rule_ids == []


@pytest.mark.parametrize(
    "text",
    [
        "校内优惠报名报名报名！！！点击点击点击！！！",
        "同一条招募信息重复发送 重复发送 重复发送 重复发送",
    ],
)
def test_marks_spam_for_revision(text: str) -> None:
    decision = moderate_content(text, context())

    assert decision.action == "revise"
    assert decision.risk_level == "medium"
    assert "spam.repetitive" in decision.rule_ids


def test_structured_fields_are_moderated_with_the_free_text() -> None:
    decision = moderate_content(
        "一起自习",
        context(structured_fields={"participation_requirements": "只要美女"}),
    )

    assert decision.action == "revise"
    assert "discrimination.recruitment" in decision.rule_ids


def test_existing_screen_result_contract_remains_available() -> None:
    result = screen_content("联系我：13800138000")

    assert isinstance(result, ScreenResult)
    assert result.has_violations is True
    assert result.risk_level in {"low", "medium", "high"}
    assert result.violations
    assert result.cleaned_text != "联系我：13800138000"
