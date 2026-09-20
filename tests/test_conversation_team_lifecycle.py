from __future__ import annotations

import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from storage.database.models import Conversation, Message, Post, Team, TeamMember, User
from storage.database.models.team import normalize_team_task_list
from storage.database.shared.model import Base
from tools import message_tools, team_tools


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            [
                User(id=1, email="owner@nju.edu.cn", password_hash="x", nickname="owner", auth_status="verified"),
                User(id=2, email="member@nju.edu.cn", password_hash="x", nickname="member", auth_status="verified"),
                User(id=3, email="other@nju.edu.cn", password_hash="x", nickname="other", auth_status="verified"),
            ]
        )
        post = Post(
            id=1,
            title="羽毛球队",
            description="周末训练",
            main_category="体育与健身",
            activity_name="羽毛球",
            current_members=2,
            target_members=2,
            status="full",
            author_id=1,
        )
        session.add(post)
        session.flush()
        session.add(
            Conversation(
                id=1,
                post_id=1,
                post_author_id=1,
                applicant_id=2,
                status="team_confirmed",
                contact_unlocked=True,
            )
        )
        team = Team(id=1, post_id=1, owner_id=1, activity_name="羽毛球", status="active")
        session.add(team)
        session.flush()
        session.add_all(
            [
                TeamMember(team_id=1, user_id=1, member_role="owner", suggested_role="队长"),
                TeamMember(team_id=1, user_id=2, member_role="member", suggested_role="队员"),
            ]
        )
        session.commit()
    return factory


def test_latest_message_page_marks_only_returned_messages_as_read(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(message_tools, "get_session", factory)
    for index in range(3):
        result = json.loads(
            message_tools.send_message.invoke(
                {"user_id": "1", "conversation_id": "1", "content": f"训练消息 {index}"}
            )
        )
        assert result["success"] is True

    before = json.loads(message_tools.get_conversations.invoke({"user_id": "2", "page": 1, "page_size": 20}))
    assert before["list"][0]["unread_count"] == 3

    page = json.loads(
        message_tools.get_messages.invoke(
            {
                "user_id": "2",
                "conversation_id": "1",
                "page": 1,
                "page_size": 2,
                "latest": True,
            }
        )
    )
    assert page["total"] == 3
    assert [message["content"] for message in page["list"]] == ["训练消息 1", "训练消息 2"]
    assert page["pagination"] == {"page": 1, "page_size": 2, "total": 3, "pages": 2}

    after = json.loads(message_tools.get_conversations.invoke({"user_id": "2", "page": 1, "page_size": 20}))
    assert after["list"][0]["unread_count"] == 1
    with factory() as session:
        messages = list(session.scalars(select(Message).order_by(Message.id)))
        assert messages[0].read_at is None
        assert all(message.read_at is not None for message in messages[1:])


def test_message_cursor_fetches_only_messages_after_the_last_seen_id(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(message_tools, "get_session", factory)
    sent_ids = []
    for index in range(3):
        result = json.loads(
            message_tools.send_message.invoke(
                {"user_id": "1", "conversation_id": "1", "content": f"增量消息 {index}"}
            )
        )
        sent_ids.append(result["message"]["id"])

    page = json.loads(
        message_tools.get_messages.invoke(
            {
                "user_id": "2",
                "conversation_id": "1",
                "page_size": 50,
                "after_id": sent_ids[0],
            }
        )
    )

    assert [message["id"] for message in page["list"]] == sent_ids[1:]


def test_team_members_can_create_complete_and_delete_tasks(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(team_tools, "get_session", factory)

    created = json.loads(
        team_tools.create_team_task.invoke(
            {
                "user_id": "2",
                "team_id": "1",
                "title": "预订场地",
                "assignee_id": "2",
                "due_at": "2026-09-20",
            }
        )
    )
    assert created["success"] is True
    task_id = created["task"]["id"]
    with factory() as session:
        persisted_tasks = session.get(Team, 1).task_list
    assert created["task"] == persisted_tasks[-1]
    assert created["team"]["task_list"] == persisted_tasks

    completed = json.loads(
        team_tools.update_team_task.invoke(
            {"user_id": "2", "team_id": "1", "task_id": task_id, "done": True}
        )
    )
    assert completed["success"] is True

    deleted = json.loads(
        team_tools.delete_team_task.invoke(
            {"user_id": "1", "team_id": "1", "task_id": task_id}
        )
    )
    assert deleted["success"] is True
    assert deleted["team"]["task_list"] == []


def test_team_members_cannot_modify_tasks_assigned_to_someone_else(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(team_tools, "get_session", factory)
    created = json.loads(
        team_tools.create_team_task.invoke(
            {
                "user_id": "1",
                "team_id": "1",
                "title": "队长任务",
                "assignee_id": "1",
                "due_at": "2026-09-20",
            }
        )
    )
    task_id = created["task"]["id"]

    completed = json.loads(
        team_tools.update_team_task.invoke(
            {"user_id": "2", "team_id": "1", "task_id": task_id, "done": True}
        )
    )
    edited = json.loads(
        team_tools.edit_team_task.invoke(
            {
                "user_id": "2",
                "team_id": "1",
                "task_id": task_id,
                "title": "被越权修改",
            }
        )
    )
    reordered = json.loads(
        team_tools.reorder_team_tasks.invoke(
            {"user_id": "2", "team_id": "1", "task_ids": task_id}
        )
    )

    assert completed == {"success": False, "message": "只能更新分配给自己的任务"}
    assert edited == {"success": False, "message": "仅队长可以编辑团队任务"}
    assert reordered == {"success": False, "message": "仅队长可以调整任务顺序"}


def test_team_task_creation_refuses_to_grow_persisted_json_past_the_limit(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(team_tools, "get_session", factory)
    with factory() as session:
        team = session.get(Team, 1)
        team.task_list = [
            {"id": f"task-{index}", "title": f"任务 {index}", "done": False}
            for index in range(12)
        ]
        session.commit()

    result = json.loads(
        team_tools.create_team_task.invoke(
            {"user_id": "1", "team_id": "1", "title": "不应写入的第十三个任务"}
        )
    )

    assert result["success"] is False
    assert "上限" in result["message"]
    with factory() as session:
        assert len(session.get(Team, 1).task_list) == 12


def test_team_task_creation_rejects_when_byte_capacity_would_drop_the_candidate(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(team_tools, "get_session", factory)
    supplementary_title = "🚀" * 120
    saturated = normalize_team_task_list(
        [
            {"id": f"large-{index}", "title": supplementary_title, "done": False}
            for index in range(12)
        ]
    )
    assert len(saturated) < 12
    assert normalize_team_task_list(
        [*saturated, {"id": "candidate", "title": supplementary_title, "done": False}]
    ) == saturated
    with factory() as session:
        team = session.get(Team, 1)
        team.task_list = saturated
        session.commit()

    result = json.loads(
        team_tools.create_team_task.invoke(
            {"user_id": "1", "team_id": "1", "title": supplementary_title}
        )
    )

    assert result == {
        "success": False,
        "message": "任务存储空间已满，请先删除或缩短现有任务",
    }
    with factory() as session:
        assert session.get(Team, 1).task_list == saturated


def test_owner_transfer_then_member_leave_updates_capacity(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(team_tools, "get_session", factory)

    transferred = json.loads(
        team_tools.transfer_team_owner.invoke(
            {"user_id": "1", "team_id": "1", "target_user_id": "2"}
        )
    )
    assert transferred["success"] is True
    assert transferred["owner_id"] == "2"

    left = json.loads(team_tools.leave_team.invoke({"user_id": "1", "team_id": "1"}))
    assert left["success"] is True
    with factory() as session:
        team = session.get(Team, 1)
        post = session.get(Post, 1)
        assert team.owner_id == 2
        assert session.scalar(
            select(TeamMember).where(TeamMember.team_id == 1, TeamMember.user_id == 1)
        ) is None
        assert post.current_members == 1
        assert post.status == "recruiting"


def test_only_owner_can_remove_members(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(team_tools, "get_session", factory)

    denied = json.loads(
        team_tools.remove_team_member.invoke(
            {"user_id": "2", "team_id": "1", "target_user_id": "1"}
        )
    )

    assert denied["success"] is False
    assert "队长" in denied["message"]


def test_team_tasks_can_be_edited_and_reordered(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(team_tools, "get_session", factory)
    task_ids = []
    for title in ("预订场地", "准备球拍"):
        created = json.loads(
            team_tools.create_team_task.invoke(
                {"user_id": "1", "team_id": "1", "title": title}
            )
        )
        task_ids.append(created["task"]["id"])

    edited = json.loads(
        team_tools.edit_team_task.invoke(
            {
                "user_id": "1",
                "team_id": "1",
                "task_id": task_ids[0],
                "title": "预订鼓楼体育馆",
                "assignee_id": "2",
                "due_at": "2026-09-20",
            }
        )
    )
    assert edited["task"]["title"] == "预订鼓楼体育馆"

    reordered = json.loads(
        team_tools.reorder_team_tasks.invoke(
            {"user_id": "1", "team_id": "1", "task_ids": ",".join(reversed(task_ids))}
        )
    )
    assert [task["id"] for task in reordered["team"]["task_list"]] == list(reversed(task_ids))


def test_owner_can_edit_member_role_and_archive_team(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(team_tools, "get_session", factory)

    role = json.loads(
        team_tools.update_team_member_role.invoke(
            {
                "user_id": "1",
                "team_id": "1",
                "target_user_id": "2",
                "suggested_role": "场地负责人",
            }
        )
    )
    assert role["success"] is True

    archived = json.loads(team_tools.archive_team.invoke({"user_id": "1", "team_id": "1"}))
    assert archived["team"]["status"] == "archived"
    rejected = json.loads(
        team_tools.create_team_task.invoke(
            {"user_id": "1", "team_id": "1", "title": "不应创建"}
        )
    )
    assert rejected["success"] is False
    assert "归档" in rejected["message"]
