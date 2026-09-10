import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.database.models.conversation import Conversation
from storage.database.models.post import Post
from storage.database.models.team import Team
from storage.database.models.user import User
from storage.database.shared.model import Base


def _confirmation_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add_all(
        [
            User(
                id=1,
                email="author@example.com",
                password_hash="hash",
                nickname="author",
                auth_status="verified",
            ),
            User(
                id=2,
                email="applicant@example.com",
                password_hash="hash",
                nickname="applicant",
                auth_status="verified",
            ),
            Post(
                id=1,
                title="组队测试",
                description="测试双向确认",
                main_category="竞赛与项目",
                activity_name="测试活动",
                target_members=2,
                needed_roles=["开发"],
                author_id=1,
            ),
            Conversation(
                id=1,
                post_id=1,
                post_author_id=1,
                applicant_id=2,
            ),
        ]
    )
    session.commit()
    session.close()
    return factory


def test_team_is_created_only_after_both_people_confirm(monkeypatch):
    from tools import message_tools

    factory = _confirmation_database()
    monkeypatch.setattr(message_tools, "get_session", factory)

    first = json.loads(
        message_tools.confirm_team.invoke(
            {"user_id": "1", "conversation_id": "1"}
        )
    )

    session = factory()
    conversation = session.get(Conversation, 1)
    assert first["success"] is True
    assert first["contact_unlocked"] is False
    assert conversation.author_confirmed is True
    assert conversation.applicant_confirmed is False
    assert session.query(Team).count() == 0
    session.close()

    second = json.loads(
        message_tools.confirm_team.invoke(
            {"user_id": "2", "conversation_id": "1"}
        )
    )

    session = factory()
    conversation = session.get(Conversation, 1)
    assert second["success"] is True
    assert second["contact_unlocked"] is True
    assert conversation.author_confirmed is True
    assert conversation.applicant_confirmed is True
    assert conversation.status == "team_confirmed"
    assert session.query(Team).count() == 1
    session.close()


def test_repeated_confirmation_by_one_person_does_not_create_team(monkeypatch):
    from tools import message_tools

    factory = _confirmation_database()
    monkeypatch.setattr(message_tools, "get_session", factory)

    message_tools.confirm_team.invoke({"user_id": "1", "conversation_id": "1"})
    repeated = json.loads(
        message_tools.confirm_team.invoke(
            {"user_id": "1", "conversation_id": "1"}
        )
    )

    session = factory()
    assert repeated["success"] is True
    assert repeated["contact_unlocked"] is False
    assert session.query(Team).count() == 0
    session.close()
