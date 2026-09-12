from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from services import moderation_cases
from storage.database.models import (
    AccountRestriction,
    Appeal,
    AuditLog,
    Conversation,
    Message,
    ModerationCase,
    ModerationEvent,
    Post,
    Report,
    Topic,
    User,
    UserBlock,
)
from storage.database.shared.model import Base


def _user(email: str, role: str = "student") -> User:
    return User(
        email=email,
        password_hash="hash",
        nickname=email.split("@", 1)[0],
        auth_status="verified",
        site_role=role,
    )


@pytest.fixture()
def sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def seeded(sessions):
    with sessions() as session:
        reporter = _user("reporter@nju.edu.cn")
        subject = _user("subject@nju.edu.cn")
        operator = _user("operator@nju.edu.cn", "operator")
        senior = _user("senior@nju.edu.cn", "senior_operator")
        session.add_all([reporter, subject, operator, senior])
        session.flush()
        post = Post(
            title="组队",
            description="正常内容",
            main_category="竞赛与项目",
            activity_name="校赛",
            target_members=3,
            author_id=subject.id,
        )
        topic = Topic(
            channel="competition",
            title="校赛",
            short_title="校赛",
            organizer="南京大学",
            organizer_key="nju",
            canonical_event_key="campus-test",
            edition="2026",
            summary="摘要",
            content="正文",
            created_by=subject.id,
        )
        session.add_all([post, topic])
        session.flush()
        conversation = Conversation(
            post_id=post.id,
            post_author_id=subject.id,
            applicant_id=reporter.id,
        )
        session.add(conversation)
        session.flush()
        message = Message(
            conversation_id=conversation.id,
            sender_id=subject.id,
            content="原始私聊内容不应进入审核日志",
        )
        session.add(message)
        session.commit()
        return {
            "reporter_id": reporter.id,
            "subject_id": subject.id,
            "operator_id": operator.id,
            "senior_id": senior.id,
            "post_id": post.id,
            "topic_id": topic.id,
            "message_id": message.id,
        }


def test_moderation_event_masks_private_text_and_audits_only_safe_metadata(sessions, seeded):
    raw = "联系微信 campusmate123，手机号13800138000，证据全文不要记录"
    with sessions() as session:
        event = moderation_cases.record_moderation_event(
            session,
            actor_id=seeded["reporter_id"],
            surface="message",
            target_type="message",
            target_id=str(seeded["message_id"]),
            action="block",
            risk_level="high",
            rule_ids=["contact.phone", "contact.wechat", "contact.phone"],
            raw_excerpt=raw,
            source="rules",
        )
        session.commit()

        assert event.rule_ids == ["contact.phone", "contact.wechat"]
        assert len(event.excerpt) <= 160
        assert "13800138000" not in event.excerpt
        assert "campusmate123" not in event.excerpt
        audit_text = " ".join(item.detail or "" for item in session.scalars(select(AuditLog)))
        assert raw not in audit_text
        assert "13800138000" not in audit_text


def test_review_event_can_create_a_paginated_operator_case(sessions, seeded):
    with sessions() as session:
        event = moderation_cases.record_moderation_event(
            session,
            actor_id=seeded["subject_id"],
            surface="post",
            target_type="post",
            target_id=str(seeded["post_id"]),
            action="review",
            risk_level="medium",
            rule_ids=["safety.manual_review"],
            raw_excerpt="只保留脱敏摘要",
            source="rules",
        )
        case = moderation_cases.create_case_from_event(
            session,
            event,
            subject_user_id=seeded["subject_id"],
            reason_code="safety.manual_review",
            priority="high",
        )
        session.commit()

        operator = session.get(User, seeded["operator_id"])
        rows, total = moderation_cases.list_cases(
            session, operator, status="open", page=1, page_size=20
        )
        assert total == 1
        assert rows[0].id == case.id
        assert case.event_id == event.id
        assert case.report_id is None
        assert case.priority == "high"


@pytest.mark.parametrize("target_type", ["post", "topic", "message", "user"])
def test_reports_support_every_target_and_create_one_open_case(sessions, seeded, target_type):
    target_id = seeded[f"{target_type}_id"] if target_type != "user" else seeded["subject_id"]
    with sessions() as session:
        reporter = session.get(User, seeded["reporter_id"])
        report, case, merged = moderation_cases.create_report(
            session,
            reporter,
            target_type=target_type,
            target_id=str(target_id),
            reason_code="unsafe_contact",
            description="请审核这个目标",
        )
        session.commit()

        assert merged is False
        assert report.status == "open"
        assert case.report_id == report.id
        assert case.status == "open"
        assert case.subject_user_id == seeded["subject_id"]


def test_duplicate_unresolved_report_is_merged_without_a_second_case(sessions, seeded):
    with sessions() as session:
        reporter = session.get(User, seeded["reporter_id"])
        first, first_case, first_merged = moderation_cases.create_report(
            session,
            reporter,
            target_type="post",
            target_id=str(seeded["post_id"]),
            reason_code="spam",
            description="第一次说明",
        )
        second, second_case, second_merged = moderation_cases.create_report(
            session,
            reporter,
            target_type="post",
            target_id=str(seeded["post_id"]),
            reason_code="harassment",
            description="第二次补充",
        )
        session.commit()

        assert first_merged is False
        assert second_merged is True
        assert second.id == first.id
        assert second_case.id == first_case.id
        assert second.report_count == 2
        assert session.query(Report).count() == 1
        assert session.query(ModerationCase).count() == 1


def test_user_blocks_are_checked_in_both_interaction_directions_and_can_be_revoked(sessions, seeded):
    with sessions() as session:
        reporter = session.get(User, seeded["reporter_id"])
        subject = session.get(User, seeded["subject_id"])

        block = moderation_cases.block_user(session, reporter, subject)
        assert block.revoked_at is None
        assert moderation_cases.users_are_blocked(session, reporter.id, subject.id) is True
        assert moderation_cases.users_are_blocked(session, subject.id, reporter.id) is True

        moderation_cases.unblock_user(session, reporter, subject)
        assert moderation_cases.users_are_blocked(session, reporter.id, subject.id) is False
        assert session.query(UserBlock).count() == 1
        assert session.query(AuditLog).filter(AuditLog.action.like("user_block.%")).count() == 2


def test_operator_queue_is_paginated_and_rejects_ordinary_users(sessions, seeded):
    with sessions() as session:
        reporter = session.get(User, seeded["reporter_id"])
        ordinary = session.get(User, seeded["subject_id"])
        operator = session.get(User, seeded["operator_id"])
        for target_type, target_id in (
            ("post", seeded["post_id"]),
            ("topic", seeded["topic_id"]),
            ("message", seeded["message_id"]),
        ):
            moderation_cases.create_report(
                session,
                reporter,
                target_type=target_type,
                target_id=str(target_id),
                reason_code="review",
            )
        session.flush()

        with pytest.raises(PermissionError):
            moderation_cases.list_cases(session, ordinary, page=1, page_size=2)
        first_page, total = moderation_cases.list_cases(session, operator, page=1, page_size=2)
        second_page, second_total = moderation_cases.list_cases(session, operator, page=2, page_size=2)

        assert total == second_total == 3
        assert len(first_page) == 2
        assert len(second_page) == 1


def test_operator_can_resolve_or_dismiss_cases_and_each_transition_is_audited(sessions, seeded):
    with sessions() as session:
        reporter = session.get(User, seeded["reporter_id"])
        operator = session.get(User, seeded["operator_id"])
        _, resolved_case, _ = moderation_cases.create_report(
            session,
            reporter,
            target_type="user",
            target_id=str(seeded["subject_id"]),
            reason_code="harassment",
        )
        _, dismissed_case, _ = moderation_cases.create_report(
            session,
            reporter,
            target_type="post",
            target_id=str(seeded["post_id"]),
            reason_code="spam",
        )
        moderation_cases.resolve_case(session, operator, resolved_case, resolution="violation_confirmed")
        moderation_cases.dismiss_case(session, operator, dismissed_case, resolution="no_violation")
        session.commit()

        assert resolved_case.status == "resolved"
        assert dismissed_case.status == "dismissed"
        assert session.get(Report, resolved_case.report_id).status == "resolved"
        assert session.get(Report, dismissed_case.report_id).status == "dismissed"
        actions = set(session.scalars(select(AuditLog.action)))
        assert {"moderation_case.resolve", "moderation_case.dismiss"} <= actions


def test_only_operator_can_create_temporary_restriction_and_expiry_disables_it(sessions, seeded):
    now = datetime.datetime.now(datetime.timezone.utc)
    with sessions() as session:
        reporter = session.get(User, seeded["reporter_id"])
        subject = session.get(User, seeded["subject_id"])
        operator = session.get(User, seeded["operator_id"])
        _, case, _ = moderation_cases.create_report(
            session,
            reporter,
            target_type="user",
            target_id=str(subject.id),
            reason_code="threat",
        )
        moderation_cases.resolve_case(session, operator, case, resolution="violation_confirmed")

        with pytest.raises(PermissionError):
            moderation_cases.create_restriction(
                session,
                reporter,
                case,
                subject,
                restriction_type="posting",
                reason_code="threat",
                expires_at=now + datetime.timedelta(hours=1),
                now=now,
            )
        restriction = moderation_cases.create_restriction(
            session,
            operator,
            case,
            subject,
            restriction_type="posting",
            reason_code="threat",
            expires_at=now + datetime.timedelta(hours=1),
            now=now,
        )
        session.commit()

        assert moderation_cases.has_active_restriction(
            session, subject.id, "posting", now=now + datetime.timedelta(minutes=30)
        ) is True
        assert moderation_cases.has_active_restriction(
            session, subject.id, "posting", now=now + datetime.timedelta(hours=2)
        ) is False
        assert restriction.expires_at is not None


def test_appeal_can_be_submitted_once_and_operator_approval_revokes_case_restrictions(sessions, seeded):
    now = datetime.datetime.now(datetime.timezone.utc)
    with sessions() as session:
        reporter = session.get(User, seeded["reporter_id"])
        subject = session.get(User, seeded["subject_id"])
        operator = session.get(User, seeded["operator_id"])
        _, case, _ = moderation_cases.create_report(
            session,
            reporter,
            target_type="user",
            target_id=str(subject.id),
            reason_code="harassment",
        )
        moderation_cases.resolve_case(session, operator, case, resolution="violation_confirmed")
        restriction = moderation_cases.create_restriction(
            session,
            operator,
            case,
            subject,
            restriction_type="all_interactions",
            reason_code="harassment",
            expires_at=now + datetime.timedelta(days=2),
            now=now,
        )
        appeal = moderation_cases.submit_appeal(
            session,
            subject,
            case,
            statement="申诉说明含有不应写进审计日志的完整证据",
        )
        with pytest.raises(ValueError):
            moderation_cases.submit_appeal(session, subject, case, statement="重复申诉")

        moderation_cases.review_appeal(
            session,
            operator,
            appeal,
            outcome="approved",
            resolution="restriction_revoked",
            now=now,
        )
        session.commit()

        assert appeal.status == "approved"
        assert restriction.revoked_at == now
        assert restriction.revoked_by == operator.id
        audit_text = " ".join(item.detail or "" for item in session.scalars(select(AuditLog)))
        assert "完整证据" not in audit_text
        assert "重复申诉" not in audit_text
        assert {"appeal.submit", "appeal.approve", "account_restriction.revoke"} <= set(
            session.scalars(select(AuditLog.action))
        )


def test_moderation_api_supports_user_reporting_and_blocking(monkeypatch, sessions, seeded):
    from api import moderation as moderation_api

    monkeypatch.setattr(moderation_api, "get_session", sessions)
    report_response = moderation_api.create_report(
        {
            "target_type": "post",
            "target_id": str(seeded["post_id"]),
            "reason_code": "spam",
            "description": "请审核",
        },
        str(seeded["reporter_id"]),
    )
    block_response = moderation_api.block_user(
        seeded["subject_id"], str(seeded["reporter_id"])
    )
    listed = moderation_api.my_reports(1, 20, str(seeded["reporter_id"]))
    unblock_response = moderation_api.unblock_user(
        seeded["subject_id"], str(seeded["reporter_id"])
    )

    assert report_response["data"]["merged"] is False
    assert report_response["data"]["report"]["target_type"] == "post"
    assert block_response["data"]["blocked_user_id"] == str(seeded["subject_id"])
    assert unblock_response["data"]["blocked"] is False
    assert listed["data"]["total"] == 1


def test_moderation_api_denies_operator_queue_and_restrictions_to_students(
    monkeypatch, sessions, seeded
):
    from api import moderation as moderation_api
    from fastapi import HTTPException

    monkeypatch.setattr(moderation_api, "get_session", sessions)
    created = moderation_api.create_report(
        {
            "target_type": "user",
            "target_id": str(seeded["subject_id"]),
            "reason_code": "threat",
        },
        str(seeded["reporter_id"]),
    )
    case_id = int(created["data"]["case"]["id"])

    with pytest.raises(HTTPException) as queue_error:
        moderation_api.operator_case_queue("open", 1, 20, str(seeded["reporter_id"]))
    with pytest.raises(HTTPException) as restriction_error:
        moderation_api.create_account_restriction(
            case_id,
            {
                "user_id": seeded["subject_id"],
                "restriction_type": "posting",
                "reason_code": "threat",
                "expires_at": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat(),
            },
            str(seeded["reporter_id"]),
        )

    assert queue_error.value.status_code == 403
    assert restriction_error.value.status_code == 403


def test_operator_case_detail_exposes_report_context_only_after_operator_check(
    monkeypatch, sessions, seeded
):
    from api import moderation as moderation_api
    from fastapi import HTTPException

    monkeypatch.setattr(moderation_api, "get_session", sessions)
    created = moderation_api.create_report(
        {
            "target_type": "message",
            "target_id": str(seeded["message_id"]),
            "reason_code": "harassment",
            "description": "对话中持续骚扰，请人工核查",
        },
        str(seeded["reporter_id"]),
    )
    case_id = int(created["data"]["case"]["id"])

    with pytest.raises(HTTPException) as denied:
        moderation_api.operator_case_detail(case_id, str(seeded["reporter_id"]))
    detail = moderation_api.operator_case_detail(case_id, str(seeded["operator_id"]))

    assert denied.value.status_code == 403
    assert detail["data"]["report"]["description"] == "对话中持续骚扰，请人工核查"
    assert detail["data"]["event"] is None


def test_moderation_api_completes_restriction_and_appeal_lifecycle(monkeypatch, sessions, seeded):
    from api import moderation as moderation_api

    monkeypatch.setattr(moderation_api, "get_session", sessions)
    created = moderation_api.create_report(
        {
            "target_type": "user",
            "target_id": str(seeded["subject_id"]),
            "reason_code": "harassment",
        },
        str(seeded["reporter_id"]),
    )
    case_id = int(created["data"]["case"]["id"])
    queue = moderation_api.operator_case_queue(
        "open", 1, 20, str(seeded["operator_id"])
    )
    resolved = moderation_api.resolve_case(
        case_id,
        {"resolution": "violation_confirmed"},
        str(seeded["operator_id"]),
    )
    restricted = moderation_api.create_account_restriction(
        case_id,
        {
            "user_id": seeded["subject_id"],
            "restriction_type": "all_interactions",
            "reason_code": "harassment",
            "expires_at": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat(),
        },
        str(seeded["operator_id"]),
    )
    appealed = moderation_api.submit_appeal(
        {"case_id": case_id, "statement": "请求复核"}, str(seeded["subject_id"])
    )
    appeal_id = int(appealed["data"]["id"])
    reviewed = moderation_api.review_appeal(
        appeal_id,
        {"outcome": "approved", "resolution": "证据不足，撤销限制"},
        str(seeded["senior_id"]),
    )

    assert queue["data"]["total"] == 1
    assert resolved["data"]["status"] == "resolved"
    assert restricted["data"]["restriction_type"] == "all_interactions"
    assert reviewed["data"]["status"] == "approved"
    with sessions() as session:
        restriction = session.get(AccountRestriction, int(restricted["data"]["id"]))
        assert restriction.revoked_at is not None
