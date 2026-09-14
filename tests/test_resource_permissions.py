import datetime
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from storage.database.models import Application, Organization, OrganizationMember, Post, Topic, User
from storage.database.shared.model import Base


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(email: str, role: str = "student") -> User:
    return User(
        email=email,
        password_hash="hash",
        nickname=email.split("@", 1)[0],
        auth_status="verified",
        site_role=role,
    )


def _topic(created_by: int, organization_id: int | None = None, channel: str = "official") -> Topic:
    return Topic(
        channel=channel,
        title="校园赛事",
        short_title="赛事",
        organizer="CampusMate",
        organizer_key="campusmate",
        canonical_event_key="event",
        edition="2026",
        summary="简介",
        content="资料",
        organization_id=organization_id,
        created_by=created_by,
    )


def _post(author_id: int, topic_id: int | None = None) -> Post:
    return Post(
        title="组队帖",
        description="招募队友",
        kind="topic_team" if topic_id else "casual_invitation",
        topic_id=topic_id,
        main_category="竞赛与项目",
        activity_name="校园赛事",
        target_members=3,
        author_id=author_id,
    )


def test_topic_roles_expose_only_their_declared_capabilities():
    from services.permissions import can_manage_topic
    from storage.database.models import TopicCollaborator

    with _session() as session:
        operator = _user("operator@nju.edu.cn", "operator")
        creator = _user("creator@nju.edu.cn")
        coordinator = _user("coordinator@nju.edu.cn")
        editor = _user("editor@nju.edu.cn")
        manager = _user("manager@nju.edu.cn")
        session.add_all([operator, creator, coordinator, editor, manager])
        session.flush()
        topic = _topic(creator.id)
        session.add(topic)
        session.flush()
        session.add_all(
            [
                TopicCollaborator(topic_id=topic.id, user_id=coordinator.id, role="coordinator", status="active", granted_by=operator.id),
                TopicCollaborator(topic_id=topic.id, user_id=editor.id, role="editor", status="active", granted_by=operator.id),
                TopicCollaborator(topic_id=topic.id, user_id=manager.id, role="manager", status="active", granted_by=operator.id),
            ]
        )
        session.flush()

        assert can_manage_topic(session, operator, topic, "manage_collaborators") is True
        assert can_manage_topic(session, coordinator, topic, "moderate_posts") is True
        assert can_manage_topic(session, coordinator, topic, "edit_topic") is False
        assert can_manage_topic(session, editor, topic, "edit_topic") is True
        assert can_manage_topic(session, editor, topic, "manage_collaborators") is False
        assert can_manage_topic(session, manager, topic, "manage_collaborators") is True


def test_pending_revoked_and_expired_topic_grants_are_inactive():
    from services.permissions import can_manage_topic
    from storage.database.models import TopicCollaborator

    with _session() as session:
        operator = _user("operator@nju.edu.cn", "operator")
        creator = _user("creator@nju.edu.cn")
        pending = _user("pending@nju.edu.cn")
        revoked = _user("revoked@nju.edu.cn")
        expired = _user("expired@nju.edu.cn")
        session.add_all([operator, creator, pending, revoked, expired])
        session.flush()
        topic = _topic(creator.id)
        session.add(topic)
        session.flush()
        session.add_all(
            [
                TopicCollaborator(topic_id=topic.id, user_id=pending.id, role="editor", status="pending", granted_by=operator.id),
                TopicCollaborator(topic_id=topic.id, user_id=revoked.id, role="editor", status="revoked", granted_by=operator.id),
                TopicCollaborator(
                    topic_id=topic.id,
                    user_id=expired.id,
                    role="editor",
                    status="active",
                    granted_by=operator.id,
                    expires_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1),
                ),
            ]
        )
        session.flush()

        assert can_manage_topic(session, pending, topic, "edit_topic") is False
        assert can_manage_topic(session, revoked, topic, "edit_topic") is False
        assert can_manage_topic(session, expired, topic, "edit_topic") is False


def test_organization_owner_and_topic_creator_can_edit_but_other_publishers_cannot():
    from services.permissions import can_manage_topic

    with _session() as session:
        owner = _user("owner@nju.edu.cn")
        creator = _user("creator@nju.edu.cn")
        other_publisher = _user("other@nju.edu.cn")
        session.add_all([owner, creator, other_publisher])
        session.flush()
        organization = Organization(name="学生会", org_type="student_org", verification_status="approved")
        session.add(organization)
        session.flush()
        session.add_all(
            [
                OrganizationMember(organization_id=organization.id, user_id=owner.id, role="owner", status="active"),
                OrganizationMember(organization_id=organization.id, user_id=creator.id, role="publisher", status="active"),
                OrganizationMember(organization_id=organization.id, user_id=other_publisher.id, role="publisher", status="active"),
            ]
        )
        topic = _topic(creator.id, organization.id, "organization")
        session.add(topic)
        session.flush()

        assert can_manage_topic(session, owner, topic, "edit_topic") is True
        assert can_manage_topic(session, creator, topic, "edit_topic") is True
        assert can_manage_topic(session, other_publisher, topic, "edit_topic") is False


def test_expired_organization_cannot_publish_or_manage_topics():
    from services.content import create_topic
    from services.permissions import can_manage_topic

    with _session() as session:
        owner = _user("expired-owner@nju.edu.cn")
        session.add(owner)
        session.flush()
        organization = Organization(
            name="Expired organization",
            org_type="student_org",
            verification_status="approved",
            expires_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1),
        )
        session.add(organization)
        session.flush()
        session.add(
            OrganizationMember(
                organization_id=organization.id,
                user_id=owner.id,
                role="owner",
                status="active",
            )
        )
        topic = _topic(owner.id, organization.id, "organization")
        session.add(topic)
        session.flush()

        assert can_manage_topic(session, owner, topic, "edit_topic") is False
        with pytest.raises(PermissionError):
            create_topic(
                session,
                owner,
                {
                    "channel": "organization",
                    "organization_id": organization.id,
                    "title": "New event",
                    "short_title": "Event",
                    "organizer": organization.name,
                    "edition": "2027",
                    "summary": "summary",
                    "content": "content",
                    "tag_ids": ["missing-tag"],
                },
            )


def test_post_roles_separate_application_management_from_content_editing():
    from services.permissions import can_manage_post
    from storage.database.models import PostCollaborator

    with _session() as session:
        author = _user("author@nju.edu.cn")
        application_manager = _user("applications@nju.edu.cn")
        editor = _user("editor@nju.edu.cn")
        session.add_all([author, application_manager, editor])
        session.flush()
        post = _post(author.id)
        session.add(post)
        session.flush()
        session.add_all(
            [
                PostCollaborator(post_id=post.id, user_id=application_manager.id, role="application_manager", status="active", granted_by=author.id),
                PostCollaborator(post_id=post.id, user_id=editor.id, role="editor", status="active", granted_by=author.id),
            ]
        )
        session.flush()

        assert can_manage_post(session, author, post, "edit_post") is True
        assert can_manage_post(session, application_manager, post, "manage_applications")
        assert can_manage_post(session, application_manager, post, "edit_post") is False
        assert can_manage_post(session, editor, post, "edit_post")


def test_topic_collaborator_invitation_requires_acceptance_and_can_be_revoked(monkeypatch):
    from api import permissions as permissions_api
    from services.permissions import can_manage_topic
    from storage.database.models import TopicCollaborator

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        operator = _user("operator@nju.edu.cn", "operator")
        invited = _user("invited@nju.edu.cn")
        session.add_all([operator, invited])
        session.flush()
        topic = _topic(operator.id)
        session.add(topic)
        session.commit()
        operator_id, invited_id, topic_id = str(operator.id), str(invited.id), topic.id
    monkeypatch.setattr(permissions_api, "get_session", sessions)

    created = permissions_api.invite_topic_collaborator(
        topic_id,
        {"user_id": invited_id, "role": "editor"},
        operator_id,
    )
    assert created["data"]["status"] == "pending"
    with sessions() as session:
        invited = session.get(User, int(invited_id))
        topic = session.get(Topic, topic_id)
        assert can_manage_topic(session, invited, topic, "edit_topic") is False

    accepted = permissions_api.accept_topic_collaboration(topic_id, invited_id)
    assert accepted["data"]["status"] == "active"
    with sessions() as session:
        invited = session.get(User, int(invited_id))
        topic = session.get(Topic, topic_id)
        assert can_manage_topic(session, invited, topic, "edit_topic") is True

    revoked = permissions_api.revoke_topic_collaborator(topic_id, int(invited_id), operator_id)
    assert revoked["data"]["status"] == "revoked"
    with sessions() as session:
        grant = session.query(TopicCollaborator).one()
        assert grant.revoked_at is not None


def test_only_topic_manager_can_invite_another_topic_collaborator(monkeypatch):
    from api import permissions as permissions_api
    from fastapi import HTTPException
    from storage.database.models import TopicCollaborator

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        operator = _user("operator@nju.edu.cn", "operator")
        editor = _user("editor@nju.edu.cn")
        manager = _user("manager@nju.edu.cn")
        target = _user("target@nju.edu.cn")
        session.add_all([operator, editor, manager, target])
        session.flush()
        topic = _topic(operator.id)
        session.add(topic)
        session.flush()
        session.add_all(
            [
                TopicCollaborator(topic_id=topic.id, user_id=editor.id, role="editor", status="active", granted_by=operator.id),
                TopicCollaborator(topic_id=topic.id, user_id=manager.id, role="manager", status="active", granted_by=operator.id),
            ]
        )
        session.commit()
        topic_id = topic.id
        editor_id, manager_id, target_id = str(editor.id), str(manager.id), str(target.id)
    monkeypatch.setattr(permissions_api, "get_session", sessions)

    try:
        permissions_api.invite_topic_collaborator(
            topic_id,
            {"user_id": target_id, "role": "coordinator"},
            editor_id,
        )
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("topic editor unexpectedly invited a collaborator")

    result = permissions_api.invite_topic_collaborator(
        topic_id,
        {"user_id": target_id, "role": "coordinator"},
        manager_id,
    )
    assert result["data"]["role"] == "coordinator"


def test_post_author_can_invite_application_manager_without_granting_edit_permission(monkeypatch):
    from api import permissions as permissions_api
    from services.permissions import can_manage_post

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        author = _user("author@nju.edu.cn")
        invited = _user("invited@nju.edu.cn")
        session.add_all([author, invited])
        session.flush()
        post = _post(author.id)
        session.add(post)
        session.commit()
        author_id, invited_id, post_id = str(author.id), str(invited.id), post.id
    monkeypatch.setattr(permissions_api, "get_session", sessions)

    permissions_api.invite_post_collaborator(
        post_id,
        {"user_id": invited_id, "role": "application_manager"},
        author_id,
    )
    permissions_api.accept_post_collaboration(post_id, invited_id)

    with sessions() as session:
        invited = session.get(User, int(invited_id))
        post = session.get(Post, post_id)
        assert can_manage_post(session, invited, post, "manage_applications") is True
        assert can_manage_post(session, invited, post, "edit_post") is False


def test_topic_editor_can_update_but_coordinator_cannot(monkeypatch):
    from api import content as content_api
    from fastapi import HTTPException
    from storage.database.models import TopicCollaborator

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        operator = _user("operator@nju.edu.cn", "operator")
        editor = _user("editor@nju.edu.cn")
        coordinator = _user("coordinator@nju.edu.cn")
        session.add_all([operator, editor, coordinator])
        session.flush()
        topic = _topic(operator.id)
        session.add(topic)
        session.flush()
        session.add_all(
            [
                TopicCollaborator(topic_id=topic.id, user_id=editor.id, role="editor", status="active", granted_by=operator.id),
                TopicCollaborator(topic_id=topic.id, user_id=coordinator.id, role="coordinator", status="active", granted_by=operator.id),
            ]
        )
        session.commit()
        topic_id = topic.id
        editor_id, coordinator_id = str(editor.id), str(coordinator.id)
    monkeypatch.setattr(content_api, "get_session", sessions)

    result = content_api.update_topic(topic_id, {"title": "更新后的赛事"}, editor_id)
    assert result["data"]["title"] == "更新后的赛事"

    with pytest.raises(HTTPException) as exc:
        content_api.update_topic(topic_id, {"title": "越权修改"}, coordinator_id)
    assert exc.value.status_code == 403


def test_post_editor_can_edit_but_application_manager_cannot(monkeypatch):
    from api import posts as posts_api
    from fastapi import HTTPException
    from storage.database.models import PostCollaborator

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        author = _user("author@nju.edu.cn")
        editor = _user("editor@nju.edu.cn")
        application_manager = _user("applications@nju.edu.cn")
        session.add_all([author, editor, application_manager])
        session.flush()
        post = _post(author.id)
        session.add(post)
        session.flush()
        session.add_all(
            [
                PostCollaborator(post_id=post.id, user_id=editor.id, role="editor", status="active", granted_by=author.id),
                PostCollaborator(post_id=post.id, user_id=application_manager.id, role="application_manager", status="active", granted_by=author.id),
            ]
        )
        session.commit()
        post_id = post.id
        editor_id, manager_id = str(editor.id), str(application_manager.id)
    monkeypatch.setattr(posts_api, "get_session", sessions)
    monkeypatch.setattr(
        posts_api,
        "classify_review",
        lambda *_args, **_kwargs: {
            "code": 0,
            "message": "ok",
            "data": {
                "main_category": "竞赛与项目",
                "tag_ids": [],
                "unknown_concepts": [],
                "risk_level": "low",
                "suggestions": [],
                "tag_proposals": [],
            },
        },
    )

    result = posts_api.update(post_id, {"title": "新的组队标题"}, editor_id)
    assert result["data"]["title"] == "新的组队标题"

    with pytest.raises(HTTPException) as exc:
        posts_api.update(post_id, {"title": "越权修改"}, manager_id)
    assert exc.value.status_code == 403


def test_topic_coordinator_can_moderate_only_posts_linked_to_topic(monkeypatch):
    from api import content as content_api
    from fastapi import HTTPException
    from storage.database.models import TopicCollaborator

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        operator = _user("operator@nju.edu.cn", "operator")
        coordinator = _user("coordinator@nju.edu.cn")
        author = _user("author@nju.edu.cn")
        session.add_all([operator, coordinator, author])
        session.flush()
        topic = _topic(operator.id)
        other_topic = _topic(operator.id)
        other_topic.canonical_event_key = "other-event"
        session.add_all([topic, other_topic])
        session.flush()
        linked_post = _post(author.id, topic.id)
        other_post = _post(author.id, other_topic.id)
        session.add_all([linked_post, other_post])
        session.flush()
        session.add(TopicCollaborator(topic_id=topic.id, user_id=coordinator.id, role="coordinator", status="active", granted_by=operator.id))
        session.commit()
        topic_id, linked_post_id, other_post_id = topic.id, linked_post.id, other_post.id
        coordinator_id = str(coordinator.id)
    monkeypatch.setattr(content_api, "get_session", sessions)

    result = content_api.moderate_topic_post(topic_id, linked_post_id, {"status": "closed"}, coordinator_id)
    assert result["data"]["status"] == "closed"

    with pytest.raises(HTTPException) as exc:
        content_api.moderate_topic_post(topic_id, other_post_id, {"status": "closed"}, coordinator_id)
    assert exc.value.status_code == 404


def test_application_manager_can_list_and_accept_applications(monkeypatch):
    from storage.database.models import Conversation, PostCollaborator, Team, TeamMember
    from tools import application_tools

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        author = _user("author@nju.edu.cn")
        manager = _user("manager@nju.edu.cn")
        applicant = _user("applicant@nju.edu.cn")
        session.add_all([author, manager, applicant])
        session.flush()
        post = _post(author.id)
        session.add(post)
        session.flush()
        application = Application(
            post_id=post.id,
            applicant_id=applicant.id,
            role_wanted="开发",
            experience="有项目经验",
            available_time="周末",
            reason="希望加入",
            status="pending",
        )
        session.add(application)
        session.add(PostCollaborator(post_id=post.id, user_id=manager.id, role="application_manager", status="active", granted_by=author.id))
        session.commit()
        post_id, application_id = str(post.id), str(application.id)
        manager_id, author_id, applicant_id = str(manager.id), author.id, applicant.id
    monkeypatch.setattr(application_tools, "get_session", sessions)

    listed = json.loads(application_tools.get_applications.invoke({"user_id": manager_id, "post_id": post_id}))
    assert listed["success"] is True
    assert listed["total"] == 1

    accepted = json.loads(application_tools.accept_application.invoke({"user_id": manager_id, "application_id": application_id}))
    assert accepted["success"] is True
    with sessions() as session:
        conversation = session.query(Conversation).one()
        assert conversation.post_author_id == author_id
        team = session.query(Team).one()
        memberships = session.query(TeamMember).filter_by(team_id=team.id).all()
        assert {(member.user_id, member.member_role) for member in memberships} == {
            (author_id, "owner"),
            (applicant_id, "member"),
        }
        assert session.get(Post, int(post_id)).current_members == 2


def test_application_manager_can_run_teammate_matching(monkeypatch):
    from api import agent
    from storage.database.models import PostCollaborator

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        author = _user("author@nju.edu.cn")
        manager = _user("manager@nju.edu.cn")
        session.add_all([author, manager])
        session.flush()
        post = _post(author.id)
        session.add(post)
        session.flush()
        session.add(PostCollaborator(post_id=post.id, user_id=manager.id, role="application_manager", status="active", granted_by=author.id))
        session.commit()
        post_id, manager_id = str(post.id), str(manager.id)
    monkeypatch.setattr(agent, "get_session", sessions)

    with sessions() as session:
        assert agent._require_post_owner(session, manager_id, post_id).id == int(post_id)
