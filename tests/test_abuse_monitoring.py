from __future__ import annotations

import datetime
import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from services import abuse_monitoring
from storage.database.models import AbuseEvent, User
from storage.database.shared.model import Base
from tools import auth_tools


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    session.add(
        User(
            id=1,
            email="student@nju.edu.cn",
            password_hash="hash",
            nickname="student",
            auth_status="verified",
        )
    )
    session.commit()
    return session


def test_repeated_identical_messages_trigger_a_short_cooldown_without_storing_text():
    session = _session()
    now = datetime.datetime.now(datetime.timezone.utc)

    decisions = [
        abuse_monitoring.check_and_record(
            session,
            user_id=1,
            event_type="message",
            target_id="conversation:7",
            content="周末一起打羽毛球",
            now=now + datetime.timedelta(seconds=index),
        )
        for index in range(4)
    ]
    session.commit()

    assert [item.action for item in decisions[:3]] == ["allow", "allow", "warn"]
    assert decisions[3].action == "cooldown"
    assert decisions[3].retry_after_seconds > 0
    events = session.scalars(select(AbuseEvent)).all()
    assert len(events) == 4
    assert all(event.content_fingerprint for event in events)
    assert all("羽毛球" not in (event.content_fingerprint or "") for event in events)


def test_ordinary_activity_across_different_targets_remains_allowed():
    session = _session()
    now = datetime.datetime.now(datetime.timezone.utc)

    decisions = [
        abuse_monitoring.check_and_record(
            session,
            user_id=1,
            event_type="message",
            target_id=f"conversation:{index}",
            content=f"正常消息 {index}",
            now=now + datetime.timedelta(seconds=index * 10),
        )
        for index in range(5)
    ]

    assert all(item.action == "allow" for item in decisions)


def test_rapid_applications_are_cooled_down_progressively():
    session = _session()
    now = datetime.datetime.now(datetime.timezone.utc)

    decisions = [
        abuse_monitoring.check_and_record(
            session,
            user_id=1,
            event_type="application",
            target_id=f"post:{index}",
            content=f"申请理由 {index}",
            now=now + datetime.timedelta(seconds=index),
        )
        for index in range(9)
    ]

    assert decisions[-2].action == "warn"
    assert decisions[-1].action == "cooldown"


def test_repeated_contact_bypass_attempts_escalate_to_manual_review():
    session = _session()
    now = datetime.datetime.now(datetime.timezone.utc)

    decisions = [
        abuse_monitoring.check_and_record(
            session,
            user_id=1,
            event_type="contact_bypass",
            target_id="conversation:7",
            content="vx abc_12345",
            now=now + datetime.timedelta(minutes=index),
        )
        for index in range(3)
    ]

    assert decisions[0].action == "warn"
    assert decisions[1].action == "cooldown"
    assert decisions[2].action == "review"


def test_network_identifier_is_hashed_before_storage():
    session = _session()
    raw_network = "203.0.113.42"

    abuse_monitoring.check_and_record(
        session,
        user_id=None,
        event_type="verification_code",
        target_id="account:masked",
        network_identifier=raw_network,
    )
    session.commit()

    event = session.scalars(select(AbuseEvent)).one()
    assert event.network_hash
    assert raw_network not in event.network_hash


def test_verification_endpoint_applies_network_cooldown(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(auth_tools, "get_session", factory)
    monkeypatch.setattr(
        auth_tools,
        "send_verification_email",
        lambda *_args, **_kwargs: {"sent": True, "message": "sent"},
    )

    results = [
        json.loads(
            auth_tools.register_auth_send_code.invoke(
                {
                    "account": "student@smail.nju.edu.cn",
                    "purpose": "register",
                    "network_identifier": "203.0.113.42",
                }
            )
        )
        for _ in range(6)
    ]

    assert all(item["sent"] is True for item in results[:5])
    assert results[5]["sent"] is False
    assert results[5]["retry_after_seconds"] > 0
    with factory() as session:
        assert session.query(AbuseEvent).count() == 6


def test_registration_submissions_apply_an_independent_network_cooldown():
    session = _session()
    now = datetime.datetime.now(datetime.timezone.utc)

    decisions = [
        abuse_monitoring.check_and_record(
            session,
            user_id=None,
            event_type="registration",
            target_id="account",
            content=f"student-{index}@smail.nju.edu.cn",
            network_identifier="203.0.113.42",
            now=now + datetime.timedelta(seconds=index),
        )
        for index in range(6)
    ]

    assert all(decision.action == "allow" for decision in decisions[:5])
    assert decisions[5].action == "cooldown"
    assert decisions[5].retry_after_seconds == 600
