from __future__ import annotations

import threading

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from api import content as content_api
from api import posts as posts_api
from services.participation import ParticipationError
from storage.database.models import Application, Conversation, Post, Team, TeamMember, Topic, User
from storage.database.shared.model import Base


def _user(email: str, *, operator: bool = False) -> User:
    return User(
        email=email,
        password_hash="hash",
        nickname=email.split("@", 1)[0],
        auth_status="verified",
        site_role="operator" if operator else "student",
    )


def _topic(owner_id: int, *, status: str = "active") -> Topic:
    return Topic(
        channel="official",
        title="Campus activity",
        short_title="Activity",
        organizer="CampusMate",
        organizer_key="campusmate",
        canonical_event_key="campus-activity",
        edition="2026",
        summary="Summary",
        content="Details",
        participation_mode="official_signup",
        capacity=20,
        status=status,
        created_by=owner_id,
    )


def _post(owner_id: int, *, topic_id: int | None = None, **overrides) -> Post:
    values = {
        "title": "Find teammates",
        "description": "Details",
        "topic_id": topic_id,
        "main_category": "Campus life",
        "activity_name": "Campus activity",
        "current_members": 1,
        "target_members": 2,
        "purpose": "team_recruitment",
        "join_mode": "application",
        "status": "recruiting",
        "author_id": owner_id,
    }
    values.update(overrides)
    return Post(**values)


def _sqlite_factory(tmp_path, name: str):
    database = tmp_path / name
    engine = create_engine(
        f"sqlite+pysqlite:///{database.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _confirmed_application(
    session,
    post: Post,
    owner: User,
    applicant: User,
    *,
    author_confirmed: bool = False,
) -> Conversation:
    application = Application(
        post_id=post.id,
        applicant_id=applicant.id,
        role_wanted="member",
        experience="experience",
        available_time="weekend",
        reason="join",
        status="accepted",
    )
    session.add(application)
    session.flush()
    conversation = Conversation(
        post_id=post.id,
        post_author_id=owner.id,
        applicant_id=applicant.id,
        application_id=application.id,
        status="active",
        author_confirmed=author_confirmed,
    )
    session.add(conversation)
    session.flush()
    return conversation


def _run_confirmation_workers(factory, calls: list[tuple[int, int]]):
    from services import participation

    barrier = threading.Barrier(len(calls))
    outcomes: list[str] = []
    unexpected: list[BaseException] = []

    def worker(conversation_id: int, user_id: int) -> None:
        try:
            with factory() as session:
                barrier.wait(timeout=10)
                result = participation.confirm_team_participation(
                    session,
                    conversation_id,
                    user_id,
                )
                session.commit()
                outcomes.append("waiting" if result.waiting_for_other else "confirmed")
        except ParticipationError as exc:
            outcomes.append(exc.code)
        except BaseException as exc:  # pragma: no cover - asserted below
            unexpected.append(exc)

    threads = [threading.Thread(target=worker, args=call) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert all(not thread.is_alive() for thread in threads)
    assert unexpected == []
    return outcomes


def test_concurrent_two_party_confirmation_creates_exactly_one_complete_team(tmp_path):
    factory = _sqlite_factory(tmp_path, "two-party-confirmation.db")
    with factory() as session:
        owner = _user("confirm-owner@nju.edu.cn")
        applicant = _user("confirm-applicant@nju.edu.cn")
        session.add_all([owner, applicant])
        session.flush()
        post = _post(owner.id)
        session.add(post)
        session.flush()
        conversation = _confirmed_application(session, post, owner, applicant)
        session.commit()
        ids = conversation.id, owner.id, applicant.id, post.id

    conversation_id, owner_id, applicant_id, post_id = ids
    outcomes = _run_confirmation_workers(
        factory,
        [(conversation_id, owner_id), (conversation_id, applicant_id)],
    )

    assert sorted(outcomes) == ["confirmed", "waiting"]
    with factory() as session:
        conversation = session.get(Conversation, conversation_id)
        post = session.get(Post, post_id)
        team = session.scalar(select(Team).where(Team.post_id == post_id))
        assert conversation.author_confirmed is True
        assert conversation.applicant_confirmed is True
        assert conversation.status == "team_confirmed"
        assert conversation.contact_unlocked is True
        assert session.scalar(select(func.count()).select_from(Team).where(Team.post_id == post_id)) == 1
        assert set(session.scalars(select(TeamMember.user_id).where(TeamMember.team_id == team.id))) == {
            owner_id,
            applicant_id,
        }
        assert post.current_members == 2
        assert post.status == "full"


def test_concurrent_confirmations_atomically_reserve_the_last_seat(tmp_path):
    factory = _sqlite_factory(tmp_path, "last-seat-confirmation.db")
    with factory() as session:
        owner = _user("seat-owner@nju.edu.cn")
        existing = _user("seat-existing@nju.edu.cn")
        first = _user("seat-first@nju.edu.cn")
        second = _user("seat-second@nju.edu.cn")
        session.add_all([owner, existing, first, second])
        session.flush()
        post = _post(owner.id, current_members=2, target_members=3)
        session.add(post)
        session.flush()
        team = Team(post_id=post.id, owner_id=owner.id, activity_name=post.activity_name)
        session.add(team)
        session.flush()
        session.add_all(
            [
                TeamMember(team_id=team.id, user_id=owner.id, member_role="owner"),
                TeamMember(team_id=team.id, user_id=existing.id, member_role="member"),
            ]
        )
        first_conversation = _confirmed_application(
            session,
            post,
            owner,
            first,
            author_confirmed=True,
        )
        second_conversation = _confirmed_application(
            session,
            post,
            owner,
            second,
            author_confirmed=True,
        )
        session.commit()
        calls = [
            (first_conversation.id, first.id),
            (second_conversation.id, second.id),
        ]
        post_id = post.id
        team_id = team.id

    outcomes = _run_confirmation_workers(factory, calls)

    assert sorted(outcomes) == ["confirmed", "participation.full"]
    with factory() as session:
        member_ids = list(
            session.scalars(select(TeamMember.user_id).where(TeamMember.team_id == team_id))
        )
        post = session.get(Post, post_id)
        conversations = list(
            session.scalars(select(Conversation).where(Conversation.id.in_([item[0] for item in calls])))
        )
        assert len(member_ids) == len(set(member_ids)) == 3
        assert post.current_members == len(member_ids)
        assert post.status == "full"
        assert sum(conversation.applicant_confirmed for conversation in conversations) == 1


def test_official_signup_commit_race_is_stable_and_recovers_the_session(tmp_path):
    from services import participation

    factory = _sqlite_factory(tmp_path, "official-signup-race.db")
    with factory() as setup:
        organizer = _user("official-race@nju.edu.cn", operator=True)
        setup.add(organizer)
        setup.flush()
        topic = _topic(organizer.id)
        setup.add(topic)
        setup.commit()
        organizer_id = organizer.id
        topic_id = topic.id

    first = factory()
    second = factory()
    try:
        first_user = first.get(User, organizer_id)
        second_user = second.get(User, organizer_id)
        first_decision = participation.validate_post_participation(
            first,
            first_user,
            {"topic_id": topic_id, "purpose": "official_signup"},
        )
        second_decision = participation.validate_post_participation(
            second,
            second_user,
            {"topic_id": topic_id, "purpose": "official_signup"},
        )
        second.rollback()

        first_post = _post(
            organizer_id,
            topic_id=topic_id,
            title="First official signup",
            purpose=first_decision.purpose,
            join_mode=first_decision.join_mode,
        )
        first.add(first_post)
        participation.commit_post_participation(first, first_post)

        second_post = _post(
            organizer_id,
            topic_id=topic_id,
            title="Competing official signup",
            purpose=second_decision.purpose,
            join_mode=second_decision.join_mode,
        )
        second.add(second_post)
        with pytest.raises(ParticipationError) as caught:
            participation.commit_post_participation(second, second_post)

        assert caught.value.code == "participation.duplicate_official_signup"
        assert "UNIQUE" not in str(caught.value).upper()
        assert second.scalar(select(func.count()).select_from(Post)) == 1

        recovery = _post(
            organizer_id,
            topic_id=topic_id,
            title="Discussion after rollback",
            purpose="discussion",
            join_mode="none",
        )
        second.add(recovery)
        participation.commit_post_participation(second, recovery)
        assert second.scalar(select(func.count()).select_from(Post)) == 2
    finally:
        first.close()
        second.close()


def test_reopen_rejects_a_replacement_official_signup_with_stable_error(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        organizer = _user("reopen-official@nju.edu.cn", operator=True)
        session.add(organizer)
        session.flush()
        topic = _topic(organizer.id)
        session.add(topic)
        session.flush()
        historical = _post(
            organizer.id,
            topic_id=topic.id,
            title="Historical official signup",
            purpose="official_signup",
            join_mode="direct",
            status="closed",
        )
        replacement = _post(
            organizer.id,
            topic_id=topic.id,
            title="Replacement official signup",
            purpose="official_signup",
            join_mode="direct",
        )
        session.add_all([historical, replacement])
        session.commit()
        ids = organizer.id, historical.id

    monkeypatch.setattr(posts_api, "get_session", factory)
    with pytest.raises(HTTPException) as caught:
        posts_api.reopen_post(ids[1], str(ids[0]))

    assert caught.value.status_code == 409
    assert caught.value.detail == {
        "code": "participation.duplicate_official_signup",
        "message": "该活动已有有效的官方报名帖",
    }
    with factory() as session:
        assert session.get(Post, ids[1]).status == "closed"


def test_topic_moderation_cannot_reactivate_a_replaced_official_signup(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        organizer = _user("moderate-official@nju.edu.cn", operator=True)
        session.add(organizer)
        session.flush()
        topic = _topic(organizer.id)
        session.add(topic)
        session.flush()
        historical = _post(
            organizer.id,
            topic_id=topic.id,
            title="Historical official signup",
            purpose="official_signup",
            join_mode="direct",
            status="hidden",
        )
        replacement = _post(
            organizer.id,
            topic_id=topic.id,
            title="Replacement official signup",
            purpose="official_signup",
            join_mode="direct",
        )
        session.add_all([historical, replacement])
        session.commit()
        ids = organizer.id, topic.id, historical.id

    monkeypatch.setattr(content_api, "get_session", factory)
    with pytest.raises(HTTPException) as caught:
        content_api.moderate_topic_post(
            ids[1],
            ids[2],
            {"status": "recruiting", "reason": "restore"},
            str(ids[0]),
        )

    assert caught.value.status_code == 409
    assert caught.value.detail == {
        "code": "participation.duplicate_official_signup",
        "message": "该活动已有有效的官方报名帖",
    }
    with factory() as session:
        assert session.get(Post, ids[2]).status == "hidden"


@pytest.mark.parametrize("topic_status", ["hidden", "missing"])
def test_join_state_and_validation_both_close_unavailable_topics(topic_status: str):
    from services import participation

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        owner = _user(f"{topic_status}-owner@nju.edu.cn")
        viewer = _user(f"{topic_status}-viewer@nju.edu.cn")
        session.add_all([owner, viewer])
        session.flush()
        topic_id = 999
        if topic_status != "missing":
            topic = _topic(owner.id, status=topic_status)
            session.add(topic)
            session.flush()
            topic_id = topic.id
        post = _post(owner.id, topic_id=topic_id)
        session.add(post)
        session.flush()

        assert participation.get_join_state(session, post, viewer.id) == "closed"
        with pytest.raises(ParticipationError) as caught:
            participation.validate_application_join(session, post, viewer)
        assert caught.value.code == "participation.closed"
